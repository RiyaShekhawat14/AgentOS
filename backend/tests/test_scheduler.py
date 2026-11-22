"""Tests for the scheduler (K5)."""
import pytest

from backend.db import models
from backend.scheduler import service
from backend.tests.conftest import make_user
from backend.tests.test_knowledge_memory import _Keep, _agent


@pytest.fixture(autouse=True)
def clean_scheduler():
    service.scheduler.remove_all_jobs()
    yield
    service.scheduler.remove_all_jobs()


@pytest.fixture()
def launched(monkeypatch):
    calls = []
    monkeypatch.setattr("backend.runs.service.launch", lambda bind, run_id: calls.append(run_id))
    return calls


def _make(client, auth, agent_id, cron="0 9 * * mon", task="Weekly sales report"):
    return client.post("/schedules", json={"agent_id": agent_id, "cron": cron, "task": task},
                       headers=auth)


def test_describe_labels():
    assert service.describe("0 9 * * *") == "Every day at 09:00"
    assert service.describe("30 18 * * mon-fri") == "Every weekday at 18:30"
    assert service.describe("0 9 * * mon") == "Every Monday at 09:00"
    assert service.describe("15 * * * *") == "Every hour at :15"
    assert service.describe("*/5 * * * *") == "*/5 * * * *"  # unknown shapes are shown as is


def test_monday_means_monday():
    # APScheduler's numeric weekdays differ from cron, so we use names. Check the name works.
    nxt = service.make_trigger("0 9 * * mon")
    assert "mon" in str(nxt).lower()


def test_login_required(client):
    assert client.get("/schedules").status_code == 401
    assert client.post("/schedules", json={}).status_code == 401


def test_create_list_toggle_delete(client, auth):
    aid = _agent(client, auth)
    res = _make(client, auth, aid)
    assert res.status_code == 201, res.text
    sch = res.json()
    assert sch["label"] == "Every Monday at 09:00"
    assert sch["next_run"] is not None
    assert service.scheduler.get_job(f"schedule-{sch['id']}") is not None

    # the agent's own schedule text is kept in sync (shown on the agents list)
    assert client.get(f"/agents/{aid}", headers=auth).json()["schedule"] == "Every Monday at 09:00"

    assert [s["id"] for s in client.get("/schedules", headers=auth).json()] == [sch["id"]]

    off = client.patch(f"/schedules/{sch['id']}", json={"enabled": False}, headers=auth).json()
    assert off["enabled"] is False and off["next_run"] is None
    assert service.scheduler.get_job(f"schedule-{sch['id']}") is None
    assert client.get(f"/agents/{aid}", headers=auth).json()["schedule"] is None

    assert client.delete(f"/schedules/{sch['id']}", headers=auth).status_code == 200
    assert client.get("/schedules", headers=auth).json() == []


def test_rejects_bad_input(client, auth):
    aid = _agent(client, auth)
    assert _make(client, auth, aid, cron="every monday").status_code == 422
    assert _make(client, auth, aid, cron="61 25 * * *").status_code == 422
    assert _make(client, auth, aid, task="   ").status_code == 422
    assert _make(client, auth, 9999).status_code == 404


def test_other_user_cannot_use_my_schedule(client, auth, launched):
    aid = _agent(client, auth)
    sid = _make(client, auth, aid).json()["id"]
    other = make_user(client, email="other@example.com", name="Other")
    assert client.get("/schedules", headers=other).json() == []
    assert _make(client, other, aid).status_code == 404          # cannot schedule on my agent
    assert client.patch(f"/schedules/{sid}", json={"enabled": False}, headers=other).status_code == 404
    assert client.delete(f"/schedules/{sid}", headers=other).status_code == 404
    assert client.post(f"/schedules/{sid}/run-now", headers=other).status_code == 404
    assert launched == []


def test_run_now_starts_a_run(client, auth, db_session, launched):
    aid = _agent(client, auth)
    sid = _make(client, auth, aid, task="Summarise sales").json()["id"]
    res = client.post(f"/schedules/{sid}/run-now", headers=auth)
    assert res.status_code == 201
    run = db_session.get(models.Run, res.json()["run_id"])
    assert run.task == "Summarise sales" and run.agent_id == aid
    assert launched == [run.id]
    assert client.get("/schedules", headers=auth).json()[0]["last_run"] is not None


def test_fire_creates_a_run(client, auth, db_session, launched, monkeypatch):
    """What the clock does when a schedule is due."""
    monkeypatch.setattr("backend.scheduler.service.SessionLocal", lambda: _Keep(db_session))
    aid = _agent(client, auth)
    sid = _make(client, auth, aid, task="Nightly check").json()["id"]
    service.fire(sid)
    runs = db_session.query(models.Run).all()
    assert [r.task for r in runs] == ["Nightly check"]
    assert launched == [runs[0].id]


def test_fire_ignores_disabled_or_deleted(client, auth, db_session, launched, monkeypatch):
    monkeypatch.setattr("backend.scheduler.service.SessionLocal", lambda: _Keep(db_session))
    aid = _agent(client, auth)
    sid = _make(client, auth, aid).json()["id"]
    client.patch(f"/schedules/{sid}", json={"enabled": False}, headers=auth)
    service.fire(sid)
    service.fire(9999)
    assert db_session.query(models.Run).count() == 0 and launched == []


def test_start_loads_enabled_schedules(client, auth, db_session, monkeypatch):
    """After a server restart, saved schedules must come back."""
    monkeypatch.setattr("backend.scheduler.service.SessionLocal", lambda: _Keep(db_session))
    aid = _agent(client, auth)
    on = _make(client, auth, aid).json()["id"]
    off = _make(client, auth, aid, cron="0 18 * * *").json()["id"]
    client.patch(f"/schedules/{off}", json={"enabled": False}, headers=auth)
    service.scheduler.remove_all_jobs()  # simulate a fresh start
    try:
        service.start()
        assert service.scheduler.get_job(f"schedule-{on}") is not None
        assert service.scheduler.get_job(f"schedule-{off}") is None
    finally:
        service.stop()
