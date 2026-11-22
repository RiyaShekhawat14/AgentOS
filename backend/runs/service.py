import threading
from datetime import datetime

from sqlalchemy.orm import Session

from backend.approval import service as approval
from backend.db.models import Agent, Run, Step
from backend.engine.graph import ACTIVE, RunEngine
from backend.engine.llm import get_llm


def create_run(db: Session, agent: Agent, task: str) -> Run:
    run = Run(agent_id=agent.id, task=task, status="running")
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def work(bind, run_id: int) -> None:
    """Runs one agent run to the end. Called from a background thread."""
    RunEngine(run_id, lambda: Session(bind=bind, autoflush=False), get_llm()).execute()


def launch(bind, run_id: int) -> None:
    """Start the run in the background so the API can answer straight away."""
    threading.Thread(target=work, args=(bind, run_id), daemon=True, name=f"run-{run_id}").start()


def stop_run(db: Session, run: Run) -> bool:
    """Stop button: end the run now. Returns False if it had already finished."""
    if run.status not in ACTIVE:
        return False
    for step in approval.pending_steps(db, run.id):
        step.status = approval.REJECTED
    db.add(Step(run_id=run.id, type="observe", output={"error": "Stopped by you."}, status="failed"))
    run.status = "failed"
    run.ended = datetime.utcnow()
    db.commit()
    return True


def step_json(step: Step) -> dict:
    return {"id": step.id, "type": step.type, "tool": step.tool, "input": step.input,
            "output": step.output, "status": step.status, "ms": step.ms}


def run_json(run: Run, steps: list[Step], agent_name: str | None = None) -> dict:
    last = next((s for s in reversed(steps) if s.type == "observe"), None)
    output = (last.output or {}) if last else {}
    return {
        "id": run.id, "agent_id": run.agent_id, "agent_name": agent_name, "task": run.task,
        "status": run.status,
        "started": run.started.isoformat() if run.started else None,
        "ended": run.ended.isoformat() if run.ended else None,
        "result": output.get("answer"), "error": output.get("error"),
        "steps": [step_json(s) for s in steps],
    }
