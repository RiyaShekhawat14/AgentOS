import json
import time

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from backend.auth.deps import get_current_user
from backend.db.models import Agent, Run, Step, User
from backend.db.session import get_db
from backend.engine.llm import get_llm
from backend.runs import service

router = APIRouter(tags=["runs"])

STREAM_POLL_SECONDS = 0.5
STREAM_MAX_SECONDS = 3600
FINISHED = ("done", "failed")


class RunIn(BaseModel):
    task: str

    @field_validator("task")
    @classmethod
    def _task(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Task cannot be empty")
        if len(v) > 2000:
            raise ValueError("Task is too long (max 2000 characters)")
        return v


def _owned_agent(agent_id: int, user: User, db: Session) -> Agent:
    agent = db.get(Agent, agent_id)
    if agent is None or agent.user_id != user.id:
        raise HTTPException(404, "Agent not found")
    return agent


def _owned_run(run_id: int, user: User, db: Session) -> tuple[Run, Agent]:
    run = db.get(Run, run_id)
    agent = db.get(Agent, run.agent_id) if run else None
    if run is None or agent is None or agent.user_id != user.id:
        raise HTTPException(404, "Run not found")
    return run, agent


def _steps(db: Session, run_id: int) -> list[Step]:
    return db.query(Step).filter(Step.run_id == run_id).order_by(Step.id).all()


def _detail(db: Session, run: Run, agent: Agent) -> dict:
    return service.run_json(run, _steps(db, run.id), agent.name)


@router.get("/llm/status")
def llm_status(user: User = Depends(get_current_user)):
    return get_llm().status()


@router.post("/agents/{agent_id}/runs", status_code=201)
def start_run(agent_id: int, body: RunIn, user: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    agent = _owned_agent(agent_id, user, db)
    run = service.create_run(db, agent, body.task)
    service.launch(db.get_bind(), run.id)
    db.refresh(run)
    return _detail(db, run, agent)


@router.get("/agents/{agent_id}/runs")
def agent_runs(agent_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    agent = _owned_agent(agent_id, user, db)
    runs = db.query(Run).filter(Run.agent_id == agent.id).order_by(Run.id.desc()).limit(50).all()
    return [service.run_json(r, [], agent.name) | {"steps": None} for r in runs]


@router.get("/runs")
def my_runs(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (db.query(Run, Agent).join(Agent, Agent.id == Run.agent_id)
            .filter(Agent.user_id == user.id).order_by(Run.id.desc()).limit(50).all())
    return [service.run_json(r, [], a.name) | {"steps": None} for r, a in rows]


@router.get("/runs/{run_id}")
def run_detail(run_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    run, agent = _owned_run(run_id, user, db)
    return _detail(db, run, agent)


@router.post("/runs/{run_id}/stop")
def stop(run_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    run, _ = _owned_run(run_id, user, db)
    if not service.stop_run(db, run):
        raise HTTPException(409, "This run has already finished")
    return {"ok": True, "status": run.status}


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


@router.get("/runs/{run_id}/stream")
def stream(run_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Live updates (Server-Sent Events): a 'step' event whenever a step is added or changes,
    a 'status' event when the run status changes, and a final 'done' event."""
    _owned_run(run_id, user, db)
    bind = db.get_bind()

    def events():
        seen: dict[int, dict] = {}
        last_status = None
        deadline = time.monotonic() + STREAM_MAX_SECONDS
        while time.monotonic() < deadline:
            session = Session(bind=bind)
            try:
                run = session.get(Run, run_id)
                steps = _steps(session, run_id)
                payload = [service.step_json(s) for s in steps]
                status, detail = run.status, service.run_json(run, steps)
            finally:
                session.close()
            sent = False
            for item in payload:
                if seen.get(item["id"]) != item:
                    seen[item["id"]] = item
                    sent = True
                    yield _sse("step", item)
            if status != last_status:
                last_status, sent = status, True
                yield _sse("status", {"status": status})
            if status in FINISHED:
                yield _sse("done", {"status": status, "result": detail["result"], "error": detail["error"]})
                return
            if not sent:
                yield ": keep-alive\n\n"
            time.sleep(STREAM_POLL_SECONDS)

    return StreamingResponse(events(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
