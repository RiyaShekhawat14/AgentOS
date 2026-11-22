from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from backend.auth.deps import get_current_user, get_owned_agent
from backend.db.models import Agent, Schedule, User
from backend.db.session import get_db
from backend.runs import service as runs_service
from backend.scheduler import service

router = APIRouter(prefix="/schedules", tags=["schedule"])


class ScheduleIn(BaseModel):
    agent_id: int
    cron: str
    task: str
    enabled: bool = True

    @field_validator("cron")
    @classmethod
    def cron_ok(cls, v: str) -> str:
        v = " ".join(v.split())
        try:
            service.make_trigger(v)
        except ValueError as e:
            raise ValueError(f"Invalid schedule: {e}")
        return v

    @field_validator("task")
    @classmethod
    def task_ok(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Task cannot be empty")
        if len(v) > 2000:
            raise ValueError("Task is too long (max 2000 characters)")
        return v


class EnabledIn(BaseModel):
    enabled: bool


def _json(s: Schedule, agent_name: str) -> dict:
    return {
        "id": s.id, "agent_id": s.agent_id, "agent_name": agent_name,
        "cron": s.cron, "label": service.describe(s.cron), "task": s.task,
        "enabled": s.enabled,
        "next_run": service.next_run_time(s.cron) if s.enabled else None,
        "last_run": s.last_run.isoformat() if s.last_run else None,
    }


def _owned(db: Session, schedule_id: int, user: User) -> tuple[Schedule, Agent]:
    s = db.get(Schedule, schedule_id)
    agent = db.get(Agent, s.agent_id) if s else None
    if s is None or agent is None or agent.user_id != user.id:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return s, agent


def _update_agent_label(db: Session, agent: Agent) -> None:
    """Keep the agent's own `schedule` text (shown on the agents list) up to date."""
    latest = (db.query(Schedule).filter(Schedule.agent_id == agent.id, Schedule.enabled.is_(True))
              .order_by(Schedule.id.desc()).first())
    agent.schedule = service.describe(latest.cron) if latest else None


@router.get("")
def list_schedules(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = (db.query(Schedule, Agent).join(Agent, Agent.id == Schedule.agent_id)
            .filter(Agent.user_id == user.id).order_by(Schedule.id).all())
    return [_json(s, a.name) for s, a in rows]


@router.post("", status_code=201)
def create_schedule(body: ScheduleIn, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    agent = get_owned_agent(db, body.agent_id, user)
    s = Schedule(agent_id=agent.id, cron=body.cron, task=body.task, enabled=body.enabled)
    db.add(s)
    db.flush()
    _update_agent_label(db, agent)
    db.commit()
    service.sync_job(s)
    return _json(s, agent.name)


@router.patch("/{schedule_id}")
def set_enabled(schedule_id: int, body: EnabledIn, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    s, agent = _owned(db, schedule_id, user)
    s.enabled = body.enabled
    db.flush()
    _update_agent_label(db, agent)
    db.commit()
    service.sync_job(s)
    return _json(s, agent.name)


@router.delete("/{schedule_id}")
def delete_schedule(schedule_id: int, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    s, agent = _owned(db, schedule_id, user)
    service.remove_job(s.id)
    db.delete(s)
    db.flush()
    _update_agent_label(db, agent)
    db.commit()
    return {"ok": True}


@router.post("/{schedule_id}/run-now", status_code=201)
def run_now(schedule_id: int, db: Session = Depends(get_db),
            user: User = Depends(get_current_user)):
    """Start the scheduled task right now (handy for testing and demos)."""
    s, agent = _owned(db, schedule_id, user)
    run = runs_service.create_run(db, agent, s.task)
    runs_service.launch(db.get_bind(), run.id)
    s.last_run = datetime.utcnow()
    db.commit()
    return {"run_id": run.id}
