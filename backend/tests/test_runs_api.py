import json

import pytest
from sqlalchemy.orm import Session

from backend.db.models import Run, Step
from backend.engine.graph import RunEngine
from backend.runs import router as runs_router
from backend.runs import service
from backend.tests.conftest import make_user
from backend.tests.test_engine import PLAN, FakeLLM, final, tool


@pytest.fixture()
def inline(monkeypatch):
    """Run the engine inside the request instead of a background thread."""
    state = {"replies": []}

    def launch(bind, run_id):
        RunEngine(run_id, lambda: Session(bind=bind, autoflush=False), FakeLLM(state["replies"]),
                  retrieve=lambda *a: [], memory_get=lambda *a: [], memory_save=lambda *a: None,
                  sleep=lambda s: None).execute()

    monkeypatch.setattr(service, "launch", launch)
    monkeypatch.setattr(runs_router, "STREAM_POLL_SECONDS", 0)
    return state


@pytest.fixture()
def agent_id(client, auth):
    return client.post("/agents", json={"name": "Analyst", "tools": ["calculator"]}, headers=auth).json()["id"]


def test_requires_login(client, agent_id):
    assert client.post(f"/agents/{agent_id}/runs", json={"task": "x"}).status_code == 401
    assert client.get("/runs").status_code == 401
    assert client.get("/runs/1").status_code == 401
    assert client.get("/llm/status").status_code == 401


def test_start_run_and_read_result(client, auth, agent_id, inline):
    inline["replies"] = [PLAN, tool("calculator", expression="12*7"), final("84")]
    res = client.post(f"/agents/{agent_id}/runs", json={"task": "  What is 12 * 7?  "}, headers=auth)
    assert res.status_code == 201
    data = client.get(f"/runs/{res.json()['id']}", headers=auth).json()
    assert data["task"] == "What is 12 * 7?" and data["agent_name"] == "Analyst"
    assert data["status"] == "done" and data["result"] == "84" and data["error"] is None
    assert [s["type"] for s in data["steps"]] == ["plan", "tool", "observe"]
    assert data["steps"][1]["tool"] == "calculator" and data["ended"]


def test_failed_run_has_error(client, auth, agent_id, inline):
    inline["replies"] = []  # the fake model has nothing to say -> error
    rid = client.post(f"/agents/{agent_id}/runs", json={"task": "x"}, headers=auth).json()["id"]
    data = client.get(f"/runs/{rid}", headers=auth).json()
    assert data["status"] == "failed" and "no more replies" in data["error"] and data["result"] is None


def test_validation(client, auth, agent_id, inline):
    for bad in ({"task": "   "}, {"task": "x" * 2001}, {}):
        assert client.post(f"/agents/{agent_id}/runs", json=bad, headers=auth).status_code == 422
    assert client.post("/agents/999/runs", json={"task": "x"}, headers=auth).status_code == 404


def test_lists(client, auth, agent_id, inline):
    inline["replies"] = [PLAN, final("a")]
    first = client.post(f"/agents/{agent_id}/runs", json={"task": "one"}, headers=auth).json()["id"]
    inline["replies"] = [PLAN, final("b")]
    second = client.post(f"/agents/{agent_id}/runs", json={"task": "two"}, headers=auth).json()["id"]
    mine = client.get("/runs", headers=auth).json()
    assert [r["id"] for r in mine] == [second, first] and mine[0]["steps"] is None
    assert mine[0]["agent_name"] == "Analyst"
    assert [r["id"] for r in client.get(f"/agents/{agent_id}/runs", headers=auth).json()] == [second, first]


def test_other_users_cannot_see_or_use(client, auth, agent_id, inline):
    inline["replies"] = [PLAN, final("a")]
    rid = client.post(f"/agents/{agent_id}/runs", json={"task": "mine"}, headers=auth).json()["id"]
    other = make_user(client, email="khushi@example.com", name="Khushi")
    assert client.get(f"/runs/{rid}", headers=other).status_code == 404
    assert client.get(f"/runs/{rid}/stream", headers=other).status_code == 404
    assert client.post(f"/runs/{rid}/stop", headers=other).status_code == 404
    assert client.post(f"/agents/{agent_id}/runs", json={"task": "x"}, headers=other).status_code == 404
    assert client.get("/runs", headers=other).json() == []
    assert client.get("/runs/999", headers=auth).status_code == 404


def test_stop(client, auth, agent_id, db_session):
    run = Run(agent_id=agent_id, task="long job", status="waiting_approval")
    db_session.add(run)
    db_session.flush()
    waiting = Step(run_id=run.id, type="tool", tool="code", input={}, status="waiting_approval")
    db_session.add(waiting)
    db_session.commit()
    res = client.post(f"/runs/{run.id}/stop", headers=auth)
    assert res.json() == {"ok": True, "status": "failed"}
    data = client.get(f"/runs/{run.id}", headers=auth).json()
    assert data["status"] == "failed" and data["error"] == "Stopped by you." and data["ended"]
    assert [s["status"] for s in data["steps"]] == ["rejected", "failed"]
    assert client.post(f"/runs/{run.id}/stop", headers=auth).status_code == 409


def parse_sse(text):
    events = []
    for block in text.strip().split("\n\n"):
        lines = [l for l in block.split("\n") if not l.startswith(":")]
        if lines:
            events.append((lines[0].removeprefix("event: "), json.loads(lines[1].removeprefix("data: "))))
    return events


def test_stream_replays_steps_and_ends_with_done(client, auth, agent_id, inline):
    inline["replies"] = [PLAN, tool("calculator", expression="2+2"), final("4")]
    rid = client.post(f"/agents/{agent_id}/runs", json={"task": "sum"}, headers=auth).json()["id"]
    res = client.get(f"/runs/{rid}/stream", headers=auth)
    assert res.headers["content-type"].startswith("text/event-stream")
    events = parse_sse(res.text)
    assert [e for e, _ in events] == ["step", "step", "step", "status", "done"]
    assert [d["type"] for e, d in events if e == "step"] == ["plan", "tool", "observe"]
    assert events[-1][1] == {"status": "done", "result": "4", "error": None}


def test_llm_status(client, auth, monkeypatch):
    class Stub:
        def status(self):
            return {"ok": False, "model": "qwen2.5", "error": "Cannot reach Ollama"}

    monkeypatch.setattr(runs_router, "get_llm", lambda: Stub())
    assert client.get("/llm/status", headers=auth).json()["error"] == "Cannot reach Ollama"
