import os
import time
from datetime import datetime
from typing import Callable, TypedDict

from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from backend.approval import service as approval
from backend.approval.policy import decide
from backend.db.models import Agent, Run, Step
from backend.engine import prompts
from backend.engine.llm import LLMError
from backend.tools.registry import describe, run_tool

MAX_STEPS = int(os.getenv("AGENT_MAX_STEPS", "8"))          # tool calls per run
RUN_TIMEOUT = float(os.getenv("AGENT_RUN_TIMEOUT", "300"))  # seconds, waiting for a human not counted
APPROVAL_TIMEOUT = float(os.getenv("AGENT_APPROVAL_TIMEOUT", "600"))
FORMAT_RETRIES = 2  # extra tries when the model does not answer in the expected JSON
ACTIVE = ("running", "waiting_approval")


class State(TypedDict, total=False):
    messages: list
    action: dict
    step_id: int
    tool_calls: int
    route: str
    answer: str
    remember: str


def _default_retrieve(agent_id, query, k=4):
    from backend.rag.service import retrieve
    return retrieve(agent_id, query, k)


def _default_memory_get(agent_id):
    from backend.memory.service import get
    return get(agent_id)


def _default_memory_save(agent_id, kind, content):
    from backend.memory.service import save
    return save(agent_id, kind, content)


class RunEngine:
    """Runs ONE agent run: plan -> choose action -> permission check -> tool -> observe -> ... -> answer.

    Everything it talks to is passed in, so tests can use a fake model and a fake clock.
    """

    def __init__(self, run_id: int, session_factory: Callable[[], Session], llm,
                 retrieve=_default_retrieve, memory_get=_default_memory_get,
                 memory_save=_default_memory_save, sleep=time.sleep, clock=time.monotonic):
        self.run_id = run_id
        self.session_factory = session_factory
        self.llm = llm
        self.retrieve, self.memory_get, self.memory_save = retrieve, memory_get, memory_save
        self.sleep, self.clock = sleep, clock
        self.db: Session | None = None
        self.run: Run | None = None
        self.agent: Agent | None = None
        self.started = 0.0
        self.waited = 0.0  # time spent waiting for a human, not counted against the timeout

    # ---------- public ----------
    def execute(self) -> None:
        self.db = self.session_factory()
        try:
            self.run = self.db.get(Run, self.run_id)
            self.agent = self.db.get(Agent, self.run.agent_id) if self.run else None
            if self.run is None or self.agent is None:
                return
            self.started = self.clock()
            self._graph().invoke({"tool_calls": 0, "route": ""},
                                 {"recursion_limit": 12 * (MAX_STEPS + 6)})
        except Exception as e:  # never leave a run stuck in "running"
            self._finish("failed", error=f"Something went wrong: {e}")
        finally:
            self.db.close()

    # ---------- database helpers ----------
    def _step(self, type_, tool=None, input_=None, output=None, status="done", ms=0) -> Step:
        step = Step(run_id=self.run.id, type=type_, tool=tool, input=input_, output=output,
                    status=status, ms=ms)
        self.db.add(step)
        self.db.commit()
        return step

    def _status(self) -> str | None:
        """'stopped' / 'timeout' / None (fine to continue). Reads fresh data every time."""
        self.db.refresh(self.run)
        if self.run.status not in ACTIVE:
            return "stopped"
        if self.clock() - self.started - self.waited > RUN_TIMEOUT:
            return "timeout"
        return None

    def _finish(self, status: str, answer: str | None = None, error: str | None = None) -> None:
        try:
            self.db.rollback()
            self.db.refresh(self.run)
            if self.run.status not in ACTIVE:
                return  # already stopped by the user
            output = {"answer": answer} if status == "done" else {"error": error}
            self._step("observe", output=output, status=status)
            self.run.status = status
            self.run.ended = datetime.utcnow()
            self.db.commit()
        except Exception:
            self.db.rollback()

    @staticmethod
    def _safe(fn, *args, default):
        try:
            return fn(*args)
        except Exception:
            return default  # knowledge / memory problems must not stop a run

    # ---------- model helper ----------
    def _ask(self, messages: list, allow_tools: bool = True):
        """Call the model until it answers in the expected JSON. Returns (action dict, raw text)."""
        convo = list(messages)
        for _ in range(FORMAT_RETRIES + 1):
            raw = self.llm.chat(convo)
            data = prompts.parse_json(raw)
            problem = prompts.check_action(data)
            if problem is None and (allow_tools or data["action"] == "final"):
                return data, raw
            convo += [{"role": "assistant", "content": raw},
                      {"role": "user", "content": prompts.FORMAT_REMINDER + f" (Problem: {problem or 'tools are not allowed now'})"}]
        raise LLMError("The model did not answer in the expected format. Try again or use a bigger model.")

    # ---------- graph ----------
    def _node(self, fn):
        def wrapped(state: State):
            try:
                return fn(state)
            except LLMError as e:
                self._finish("failed", error=str(e))
            except Exception as e:
                self._finish("failed", error=f"Something went wrong: {e}")
            return {"route": "end"}
        return wrapped

    def _graph(self):
        g = StateGraph(State)
        for name, fn in [("init", self._init), ("plan", self._plan), ("decide", self._decide),
                         ("guard", self._guard), ("approve", self._approve),
                         ("execute", self._execute), ("finish", self._finish_node)]:
            g.add_node(name, self._node(fn))
        route = lambda s: s.get("route", "end")  # noqa: E731
        g.add_edge(START, "init")
        g.add_conditional_edges("init", route, {"plan": "plan", "end": END})
        g.add_conditional_edges("plan", route, {"decide": "decide", "end": END})
        g.add_conditional_edges("decide", route, {"final": "finish", "tool": "guard", "end": END})
        g.add_conditional_edges("guard", route, {"execute": "execute", "approve": "approve",
                                                 "decide": "decide", "end": END})
        g.add_conditional_edges("approve", route, {"execute": "execute", "decide": "decide", "end": END})
        g.add_conditional_edges("execute", route, {"decide": "decide", "end": END})
        g.add_edge("finish", END)
        return g.compile()

    def _alive_or_end(self):
        """Returns {'route': 'end'} when the run must stop now, otherwise None."""
        problem = self._status()
        if problem == "timeout":
            self._finish("failed", error=f"The run took longer than {int(RUN_TIMEOUT)} seconds and was stopped.")
        return {"route": "end"} if problem else None

    def _init(self, state: State):
        agent, run = self.agent, self.run
        usable = [t for t in agent.tools or []
                  if decide(agent.tools, agent.permissions, t).mode != "blocked"]
        memory = self._safe(self.memory_get, agent.id, default=[])
        docs = self._safe(self.retrieve, agent.id, run.task, 4, default=[])
        system = prompts.build_system_prompt(agent.instructions or "", describe(usable), memory, docs)
        return {"route": "plan", "messages": [{"role": "system", "content": system},
                                              {"role": "user", "content": f"Task: {run.task}"}]}

    def _plan(self, state: State):
        stop = self._alive_or_end()
        if stop:
            return stop
        t0 = self.clock()
        messages = state["messages"] + [{"role": "user", "content": prompts.PLAN_REQUEST}]
        plan = []
        data = prompts.parse_json(self.llm.chat(messages)) or {}
        if isinstance(data.get("plan"), list):
            plan = [str(p)[:300] for p in data["plan"][:6]]
        self._step("plan", output={"plan": plan}, ms=int((self.clock() - t0) * 1000))
        note = "Your plan: " + "; ".join(plan) if plan else "Work step by step."
        return {"route": "decide", "messages": state["messages"] + [{"role": "user", "content": note}]}

    def _decide(self, state: State):
        stop = self._alive_or_end()
        if stop:
            return stop
        messages = state["messages"]
        out_of_calls = state["tool_calls"] >= MAX_STEPS
        if out_of_calls:
            messages = messages + [{"role": "user", "content": prompts.FORCE_FINAL}]
        action, raw = self._ask(messages, allow_tools=not out_of_calls)
        update = {"messages": state["messages"] + [{"role": "assistant", "content": raw}], "action": action}
        if action["action"] == "final":
            return {**update, "route": "final", "answer": action["answer"].strip(),
                    "remember": str(action.get("remember") or "").strip()}
        return {**update, "route": "tool"}

    def _guard(self, state: State):
        stop = self._alive_or_end()
        if stop:
            return stop
        action = state["action"]
        tool, args = action["tool"].strip(), action.get("args") or {}
        verdict = decide(self.agent.tools, self.agent.permissions, tool)
        if verdict.mode == "blocked":
            self._step("tool", tool, args, {"ok": False, "error": verdict.reason, "thought": action.get("thought")},
                       status="blocked")
            return self._observed(state, tool, {"ok": False, "error": f"Not allowed: {verdict.reason}"})
        if verdict.mode == "ask":
            step = self._step("tool", tool, args, None, status="running")
            approval.request_approval(self.db, self.run, step)
            return {"route": "approve", "step_id": step.id}
        step = self._step("tool", tool, args, None, status="running")
        return {"route": "execute", "step_id": step.id}

    def _approve(self, state: State):
        t0 = self.clock()
        outcome = approval.wait_for_decision(self.session_factory, state["step_id"],
                                             timeout=APPROVAL_TIMEOUT, sleep=self.sleep)
        self.waited += self.clock() - t0
        if outcome == "cancelled":
            return {"route": "end"}
        self.db.expire_all()
        step = self.db.get(Step, state["step_id"])
        if outcome == "approved":
            step.status = "running"
            self.db.commit()
            return {"route": "execute"}
        reason = ("No one answered in time, so the action was not run." if outcome == "timeout"
                  else "The user rejected this action.")
        step.output = {"ok": False, "error": reason, "thought": state["action"].get("thought")}
        self.db.commit()
        return self._observed(state, step.tool, {"ok": False, "error": reason})

    def _execute(self, state: State):
        stop = self._alive_or_end()
        if stop:
            return stop
        action = state["action"]
        tool, args = action["tool"].strip(), action.get("args") or {}
        t0 = self.clock()
        result = run_tool(tool, args, self.agent.id)
        step = self.db.get(Step, state["step_id"])
        step.status = "done" if result["ok"] else "failed"
        step.output = {**result, "thought": action.get("thought")}
        step.ms = int((self.clock() - t0) * 1000)
        self.db.commit()
        return self._observed(state, tool, result)

    def _observed(self, state: State, tool: str, result: dict):
        """Tell the model what happened and go back to choosing the next action."""
        text = f"Result of {tool}: " + prompts.shorten(result)
        if not result.get("ok"):
            text += "\nThat did not work. Fix the input, try another way, or explain the problem in your final answer."
        return {"route": "decide", "tool_calls": state["tool_calls"] + 1,
                "messages": state["messages"] + [{"role": "user", "content": text}]}

    def _finish_node(self, state: State):
        answer = state["answer"]
        task = self.run.task
        self._safe(self.memory_save, self.agent.id, "short",
                   f"Task: {task[:200]} | Result: {answer[:300]}", default=None)
        if state.get("remember"):
            self._safe(self.memory_save, self.agent.id, "long", state["remember"][:500], default=None)
        self._finish("done", answer=answer)
        return {"route": "end"}
