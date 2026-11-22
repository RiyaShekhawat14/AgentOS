import pytest

from backend.approval import service
from backend.approval.policy import DEFAULT_MODES, decide
from backend.db.models import Agent, Run, Step
from backend.tests.conftest import make_user


# ---- policy ----
def test_defaults_ask_only_for_code():
    tools = list(DEFAULT_MODES)
    assert {t: decide(tools, {}, t).mode for t in tools} == {
        "web_search": "auto", "calculator": "auto", "csv_reader": "auto", "code": "ask"}


def test_agent_setting_wins_over_default():
    assert decide(["code"], {"code": "auto"}, "code").mode == "auto"
    assert decide(["calculator"], {"calculator": "ask"}, "calculator").mode == "ask"
    assert decide(["web_search"], {"web_search": "blocked"}, "web_search").mode == "blocked"


def test_tool_not_enabled_or_unknown_is_blocked():
    assert decide(["calculator"], {}, "code").mode == "blocked"
    assert decide(None, None, "calculator").mode == "blocked"
    assert decide(["files"], {}, "files").mode == "blocked"  # old seed name, not a real tool
    assert "not enabled" in decide(["calculator"], {}, "code").reason


def test_bad_permission_value_falls_back_to_ask():
    d = decide(["calculator"], {"calculator": "yolo"}, "calculator")
    assert d.mode == "ask" and "yolo" in d.reason


# ---- service ----
def make_run(db, user_id=1, status="running", tool="code"):
    agent = Agent(user_id=user_id, name="A", instructions="", tools=[tool], permissions={})
    db.add(agent)
    db.flush()
    run = Run(agent_id=agent.id, task="do it", status=status)
    db.add(run)
    db.flush()
    step = Step(run_id=run.id, type="tool", tool=tool, input={"code": "print(1)"})
    db.add(step)
    db.commit()
    return run, step


@pytest.fixture()
def user_id(client):
    make_user(client)
    return 1


def test_request_then_approve(db_session, user_id):
    run, step = make_run(db_session, user_id)
    service.request_approval(db_session, run, step)
    assert (run.status, step.status) == ("waiting_approval", "waiting_approval")
    assert [s.id for s in service.pending_steps(db_session, run.id)] == [step.id]
    service.decide_step(db_session, run, step, True)
    assert (run.status, step.status) == ("running", "approved")
    assert service.pending_steps(db_session, run.id) == []


def test_reject_and_double_answer(db_session, user_id):
    run, step = make_run(db_session, user_id)
    service.request_approval(db_session, run, step)
    service.decide_step(db_session, run, step, False)
    assert step.status == "rejected"
    with pytest.raises(service.ApprovalError):
        service.decide_step(db_session, run, step, True)


def test_run_keeps_waiting_while_another_step_is_pending(db_session, user_id):
    run, first = make_run(db_session, user_id)
    second = Step(run_id=run.id, type="tool", tool="code", input={})
    db_session.add(second)
    db_session.commit()
    service.request_approval(db_session, run, first)
    service.request_approval(db_session, run, second)
    service.decide_step(db_session, run, first, True)
    assert run.status == "waiting_approval"
    service.decide_step(db_session, run, second, True)
    assert run.status == "running"


def test_step_from_other_run_is_refused(db_session, user_id):
    run, step = make_run(db_session, user_id)
    other_run, _ = make_run(db_session, user_id)
    service.request_approval(db_session, run, step)
    with pytest.raises(service.ApprovalError):
        service.decide_step(db_session, other_run, step, True)


# ---- waiting ----
def factory(db_session):
    return lambda: _Borrowed(db_session)


class _Borrowed:
    """Lets wait_for_decision 'close' the shared test session without really closing it."""
    def __init__(self, s): self._s = s
    def __getattr__(self, name): return getattr(self._s, name)
    def close(self): pass


def test_wait_returns_when_human_approves(db_session, user_id):
    run, step = make_run(db_session, user_id)
    service.request_approval(db_session, run, step)
    calls = []

    def human_answers(_seconds):
        calls.append(1)
        if len(calls) == 3:
            service.decide_step(db_session, run, step, True)

    out = service.wait_for_decision(factory(db_session), step.id, timeout=60, poll=1, sleep=human_answers)
    assert out == "approved" and len(calls) == 3


def test_wait_returns_rejected(db_session, user_id):
    run, step = make_run(db_session, user_id)
    service.request_approval(db_session, run, step)
    service.decide_step(db_session, run, step, False)
    assert service.wait_for_decision(factory(db_session), step.id, sleep=lambda s: None) == "rejected"


def test_wait_times_out_and_rejects(db_session, user_id):
    run, step = make_run(db_session, user_id)
    service.request_approval(db_session, run, step)
    out = service.wait_for_decision(factory(db_session), step.id, timeout=3, poll=1, sleep=lambda s: None)
    assert out == "timeout" and step.status == "rejected" and "in time" in step.output["error"]


def test_wait_cancelled_when_run_is_stopped(db_session, user_id):
    run, step = make_run(db_session, user_id)
    service.request_approval(db_session, run, step)
    run.status = "failed"
    db_session.commit()
    assert service.wait_for_decision(factory(db_session), step.id, sleep=lambda s: None) == "cancelled"
    assert service.wait_for_decision(factory(db_session), 9999, sleep=lambda s: None) == "cancelled"


# ---- API ----
def test_api_flow_and_ownership(client, db_session):
    owner = make_user(client)
    other = make_user(client, email="khushi@example.com", name="Khushi")
    run, step = make_run(db_session, user_id=1)
    service.request_approval(db_session, run, step)
    base = f"/runs/{run.id}"

    assert client.get(f"{base}/approvals").status_code == 401
    assert client.get(f"{base}/approvals", headers=other).status_code == 404
    assert client.post(f"{base}/steps/{step.id}/approve", headers=other).status_code == 404

    pending = client.get(f"{base}/approvals", headers=owner).json()
    assert pending == [{"step_id": step.id, "tool": "code", "input": {"code": "print(1)"}}]

    res = client.post(f"{base}/steps/{step.id}/approve", headers=owner)
    assert res.json() == {"ok": True, "step_id": step.id, "status": "approved", "run_status": "running"}
    assert client.get(f"{base}/approvals", headers=owner).json() == []
    assert client.post(f"{base}/steps/{step.id}/reject", headers=owner).status_code == 409


def test_api_reject_and_not_found(client, db_session):
    owner = make_user(client)
    run, step = make_run(db_session, user_id=1)
    service.request_approval(db_session, run, step)
    assert client.post(f"/runs/{run.id}/steps/{step.id}/reject", headers=owner).json()["status"] == "rejected"
    assert client.post(f"/runs/{run.id}/steps/999/approve", headers=owner).status_code == 404
    assert client.get("/runs/999/approvals", headers=owner).status_code == 404
    other_run, other_step = make_run(db_session, user_id=1)
    assert client.post(f"/runs/{run.id}/steps/{other_step.id}/approve", headers=owner).status_code == 404
