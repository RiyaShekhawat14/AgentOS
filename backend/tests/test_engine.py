import json

import pytest
from sqlalchemy.orm import Session

from backend.approval import service as approval
from backend.db.models import Agent, Run, Step
from backend.engine import graph
from backend.engine.graph import RunEngine
from backend.engine.llm import LLMError
from backend.tests.conftest import make_user

PLAN = {"plan": ["look at the task", "answer"]}


def tool(name, **args):
    return {"action": "tool", "thought": f"use {name}", "tool": name, "args": args}


def final(text, **extra):
    return {"action": "final", "answer": text, **extra}


class FakeLLM:
    """Plays back prepared replies and remembers what it was asked."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def chat(self, messages):
        self.calls.append(list(messages))
        if not self.replies:
            raise LLMError("fake model has no more replies")
        reply = self.replies.pop(0)
        if callable(reply):
            reply = reply()
        if isinstance(reply, Exception):
            raise reply
        return reply if isinstance(reply, str) else json.dumps(reply)


@pytest.fixture()
def setup(client, db_session):
    make_user(client)

    def _setup(tools=("calculator",), permissions=None, instructions="Be brief."):
        agent = Agent(user_id=1, name="Analyst", instructions=instructions,
                      tools=list(tools), permissions=permissions or {})
        db_session.add(agent)
        db_session.flush()
        run = Run(agent_id=agent.id, task="What is 12 * 7?", status="running")
        db_session.add(run)
        db_session.commit()
        return run.id

    return _setup


def factory(db_session):
    bind = db_session.get_bind()
    return lambda: Session(bind=bind, autoflush=False)


def run_engine(db_session, run_id, replies, **kw):
    llm = FakeLLM(replies)
    kw.setdefault("retrieve", lambda *a: [])
    kw.setdefault("memory_get", lambda *a: [])
    kw.setdefault("memory_save", lambda *a: None)
    kw.setdefault("sleep", lambda s: None)
    RunEngine(run_id, factory(db_session), llm, **kw).execute()
    db_session.expire_all()
    return llm, db_session.get(Run, run_id), db_session.query(Step).filter_by(run_id=run_id).order_by(Step.id).all()


def test_answer_without_tools(setup, db_session):
    rid = setup(tools=())
    llm, run, steps = run_engine(db_session, rid, [PLAN, final("84")])
    assert run.status == "done" and run.ended is not None
    assert [(s.type, s.status) for s in steps] == [("plan", "done"), ("observe", "done")]
    assert steps[0].output == {"plan": PLAN["plan"]}
    assert steps[1].output == {"answer": "84"}
    assert "You have no tools" in llm.calls[0][0]["content"]


def test_tool_then_answer(setup, db_session):
    rid = setup()
    llm, run, steps = run_engine(db_session, rid, [PLAN, tool("calculator", expression="12*7"), final("It is 84")])
    assert run.status == "done"
    assert [s.type for s in steps] == ["plan", "tool", "observe"]
    t = steps[1]
    assert (t.tool, t.status, t.input) == ("calculator", "done", {"expression": "12*7"})
    assert t.output["ok"] and t.output["result"]["result"] == 84 and t.output["thought"] == "use calculator"
    assert "Result of calculator" in llm.calls[-1][-1]["content"]  # the model saw the observation


def test_tool_failure_is_shown_and_model_can_recover(setup, db_session):
    rid = setup()
    llm, run, steps = run_engine(db_session, rid, [
        PLAN, tool("calculator", expression="1/0"), tool("calculator", expression="12*7"), final("84")])
    assert run.status == "done"
    assert [s.status for s in steps if s.type == "tool"] == ["failed", "done"]
    assert "Division by zero" in llm.calls[2][-1]["content"]


def test_blocked_tool_never_runs(setup, db_session):
    rid = setup(permissions={"calculator": "blocked"})
    llm, run, steps = run_engine(db_session, rid, [PLAN, tool("calculator", expression="1+1"), final("sorry")])
    assert run.status == "done"
    t = [s for s in steps if s.type == "tool"][0]
    assert t.status == "blocked" and not t.output["ok"]
    assert "calculator" not in llm.calls[0][0]["content"].split("Always reply")[0]  # hidden from the prompt
    assert "Not allowed" in llm.calls[2][-1]["content"]


def test_unknown_or_disabled_tool_is_blocked(setup, db_session):
    rid = setup(tools=("calculator",))
    _, run, steps = run_engine(db_session, rid, [PLAN, tool("code", code="print(1)"), tool("hack"), final("done")])
    assert run.status == "done"
    assert [s.status for s in steps if s.type == "tool"] == ["blocked", "blocked"]


def _approver(db_session, run_id, approve):
    def answer(_seconds):
        s = factory(db_session)()
        try:
            run = s.get(Run, run_id)
            step = approval.pending_steps(s, run_id)[0]
            approval.decide_step(s, run, step, approve)
        finally:
            s.close()
    return answer


def test_ask_then_approved_runs_the_tool(setup, db_session):
    rid = setup(tools=("code",))
    _, run, steps = run_engine(db_session, rid, [PLAN, tool("code", code="print(1 + 1)"), final("2")],
                               sleep=_approver(db_session, rid, True))
    t = [s for s in steps if s.type == "tool"][0]
    assert run.status == "done"
    assert t.status == "done" and t.output["result"]["output"].strip() == "2"


def test_ask_then_rejected_does_not_run_the_tool(setup, db_session):
    rid = setup(tools=("code",))
    llm, run, steps = run_engine(db_session, rid, [PLAN, tool("code", code="print(1)"), final("ok, skipped")],
                                 sleep=_approver(db_session, rid, False))
    t = [s for s in steps if s.type == "tool"][0]
    assert run.status == "done" and t.status == "rejected"
    assert "rejected" in t.output["error"]
    assert "rejected" in llm.calls[2][-1]["content"]


def test_ask_can_be_set_for_any_tool(setup, db_session):
    rid = setup(permissions={"calculator": "ask"})
    seen = []

    def sleep(s):
        seen.append(db_session.get(Run, rid).status)
        _approver(db_session, rid, True)(s)

    _, run, steps = run_engine(db_session, rid, [PLAN, tool("calculator", expression="2+2"), final("4")], sleep=sleep)
    assert seen == ["waiting_approval"] and run.status == "done"


def test_approval_timeout_rejects(setup, db_session, monkeypatch):
    rid = setup(tools=("code",))
    monkeypatch.setattr(graph, "APPROVAL_TIMEOUT", 2)
    _, run, steps = run_engine(db_session, rid, [PLAN, tool("code", code="print(1)"), final("gave up")])
    t = [s for s in steps if s.type == "tool"][0]
    assert t.status == "rejected" and "in time" in t.output["error"] and run.status == "done"


def test_bad_json_is_retried(setup, db_session):
    rid = setup(tools=())
    llm, run, _ = run_engine(db_session, rid, [PLAN, "I think it is 84", "{oops", "Sure! " + json.dumps(final("84")) + " bye"])
    assert run.status == "done" and len(llm.calls) == 4
    assert "not valid" in llm.calls[2][-1]["content"]


def test_gives_up_after_too_many_bad_answers(setup, db_session):
    rid = setup(tools=())
    _, run, steps = run_engine(db_session, rid, [PLAN, "no", "still no", "never"])
    assert run.status == "failed" and "expected format" in steps[-1].output["error"]


def test_model_unreachable_fails_cleanly(setup, db_session):
    rid = setup()
    _, run, steps = run_engine(db_session, rid, [LLMError("Cannot reach Ollama at http://localhost:11434")])
    assert run.status == "failed" and run.ended is not None
    assert steps[-1].type == "observe" and "Cannot reach Ollama" in steps[-1].output["error"]


def test_step_limit_forces_a_final_answer(setup, db_session, monkeypatch):
    rid = setup()
    monkeypatch.setattr(graph, "MAX_STEPS", 2)
    llm, run, steps = run_engine(db_session, rid, [
        PLAN, tool("calculator", expression="1+1"), tool("calculator", expression="2+2"),
        tool("calculator", expression="3+3"),  # not allowed any more, model is told and must answer
        final("best answer")])
    assert run.status == "done" and len([s for s in steps if s.type == "tool"]) == 2
    assert steps[-1].output == {"answer": "best answer"}
    assert "all the tool calls" in llm.calls[3][-1]["content"]


def test_stopped_by_user_ends_quietly(setup, db_session):
    rid = setup()

    def user_presses_stop():
        s = factory(db_session)()
        try:
            from backend.runs.service import stop_run
            stop_run(s, s.get(Run, rid))
        finally:
            s.close()
        return tool("calculator", expression="1+1")

    _, run, steps = run_engine(db_session, rid, [PLAN, user_presses_stop])
    assert run.status == "failed"
    assert [(s.type, s.status) for s in steps] == [("plan", "done"), ("observe", "failed")]
    assert steps[-1].output == {"error": "Stopped by you."}  # written by stop, not by the engine


def test_timeout(setup, db_session, monkeypatch):
    rid = setup()
    monkeypatch.setattr(graph, "RUN_TIMEOUT", 50)
    ticks = iter(range(0, 10_000, 100))
    llm, run, steps = run_engine(db_session, rid, [PLAN], clock=lambda: next(ticks))
    assert run.status == "failed" and "longer than 50 seconds" in steps[-1].output["error"]
    assert llm.calls == []


def test_memory_and_knowledge_are_used_and_saved(setup, db_session):
    rid = setup(tools=())
    saved = []
    llm, run, _ = run_engine(
        db_session, rid, [PLAN, final("Revenue is up", remember="Owner prefers INR")],
        retrieve=lambda agent_id, q, k: [{"text": "Revenue was 5 lakh", "source": "Sales.pdf", "score": 0.9}],
        memory_get=lambda agent_id: [{"id": 1, "kind": "long", "content": "Report in tables"}],
        memory_save=lambda agent_id, kind, content: saved.append((kind, content)))
    system = llm.calls[0][0]["content"]
    assert "[Sales.pdf] Revenue was 5 lakh" in system and "(long) Report in tables" in system
    assert "Be brief." in system
    assert saved[0][0] == "short" and "What is 12 * 7?" in saved[0][1] and "Revenue is up" in saved[0][1]
    assert saved[1] == ("long", "Owner prefers INR")


def test_broken_knowledge_or_memory_does_not_stop_the_run(setup, db_session):
    rid = setup(tools=())

    def boom(*a):
        raise RuntimeError("embedding model missing")

    _, run, _ = run_engine(db_session, rid, [PLAN, final("fine")], retrieve=boom, memory_get=boom, memory_save=boom)
    assert run.status == "done"
