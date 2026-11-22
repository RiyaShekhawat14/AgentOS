"""Tests for GET /metrics (the dashboard numbers)."""
from datetime import datetime, timedelta

from backend.db import models
from backend.tests.conftest import make_user


def _agent(client, headers):
    return client.post("/agents", json={"name": "A", "tools": ["calculator"]}, headers=headers).json()["id"]


def _run(db, agent_id, status, seconds=30, days_ago=0, tool=None):
    start = datetime.utcnow() - timedelta(days=days_ago)
    run = models.Run(agent_id=agent_id, task="t", status=status, started=start,
                     ended=start + timedelta(seconds=seconds) if status in ("done", "failed") else None)
    db.add(run)
    db.flush()
    if tool:
        db.add(models.Step(run_id=run.id, type="tool", tool=tool, ms=5))
    db.commit()


def test_login_required(client):
    assert client.get("/metrics").status_code == 401


def test_empty_user(client, auth):
    m = client.get("/metrics", headers=auth).json()
    assert m["agents"] == 0 and m["tasks_run"] == 0 and m["success_rate"] == 0
    assert m["runs_per_day"] == [] and m["tool_usage"] == [] and m["recent_runs"] == []


def test_numbers(client, auth, db_session):
    aid = _agent(client, auth)
    _run(db_session, aid, "done", seconds=20, tool="calculator")
    _run(db_session, aid, "done", seconds=40, days_ago=1, tool="calculator")
    _run(db_session, aid, "failed", seconds=60, days_ago=1, tool="csv_reader")
    _run(db_session, aid, "running")
    m = client.get("/metrics", headers=auth).json()
    assert m["agents"] == 1
    assert m["tasks_run"] == 4
    assert m["success_rate"] == 66.7          # 2 done of 3 finished (running not counted)
    assert m["avg_seconds"] == 40.0           # (20 + 40 + 60) / 3
    assert m["tool_calls"] == 3
    assert {t["tool"]: t["count"] for t in m["tool_usage"]} == {"calculator": 2, "csv_reader": 1}
    assert sum(d["count"] for d in m["runs_per_day"]) == 4
    assert len(m["recent_runs"]) == 4


def test_users_only_see_their_own_numbers(client, auth, db_session):
    aid = _agent(client, auth)
    _run(db_session, aid, "done", tool="calculator")
    other = make_user(client, email="other@example.com", name="Other")
    m = client.get("/metrics", headers=other).json()
    assert m["tasks_run"] == 0 and m["agents"] == 0 and m["tool_calls"] == 0
