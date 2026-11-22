from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from backend.db.session import get_db
from backend.db.models import Run, Step, Agent
from backend.auth.deps import get_current_user

router = APIRouter(tags=["metrics"])

@router.get("/metrics")
def metrics(db: Session = Depends(get_db), user=Depends(get_current_user)):
    my_agents = select(Agent.id).where(Agent.user_id == user.id)
    mine = Run.agent_id.in_(my_agents)

    total = db.scalar(select(func.count(Run.id)).where(mine)) or 0
    done = db.scalar(select(func.count(Run.id)).where(mine, Run.status == "done")) or 0
    failed = db.scalar(select(func.count(Run.id)).where(mine, Run.status == "failed")) or 0
    finished = done + failed
    success_rate = round(100 * done / finished, 1) if finished else 0

    agents = db.scalar(select(func.count(Agent.id)).where(Agent.user_id == user.id)) or 0

    # Average run time, worked out here (not in SQL) so it behaves the same on every database.
    finished_runs = db.execute(
        select(Run.started, Run.ended).where(mine, Run.ended.is_not(None))
        .order_by(Run.id.desc()).limit(1000)
    ).all()
    secs = [(e - s).total_seconds() for s, e in finished_runs if s and e]
    avg_secs = sum(secs) / len(secs) if secs else 0

    tool_calls = db.scalar(
        select(func.count(Step.id)).join(Run, Run.id == Step.run_id)
        .where(mine, Step.type == "tool")
    ) or 0

    since = datetime.utcnow() - timedelta(days=7)
    per_day = db.execute(
        select(func.date(Run.started).label("day"), func.count(Run.id))
        .where(mine, Run.started >= since).group_by("day").order_by("day")
    ).all()

    usage = db.execute(
        select(Step.tool, func.count(Step.id))
        .join(Run, Run.id == Step.run_id)
        .where(mine, Step.tool.is_not(None)).group_by(Step.tool)
    ).all()

    recent = db.execute(
        select(Run.id, Run.task, Run.status, Agent.name)
        .join(Agent, Agent.id == Run.agent_id)
        .where(Agent.user_id == user.id).order_by(Run.id.desc()).limit(5)
    ).all()

    return {
        "agents": agents,
        "tasks_run": total,
        "success_rate": success_rate,
        "avg_seconds": round(avg_secs or 0, 1),
        "tool_calls": tool_calls,
        "runs_per_day": [{"day": str(d), "count": c} for d, c in per_day],
        "tool_usage": [{"tool": t, "count": c} for t, c in usage],
        "recent_runs": [{"id": i, "task": t, "status": s, "agent": a} for i, t, s, a in recent],
    }