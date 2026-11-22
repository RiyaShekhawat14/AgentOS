from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.approval import service
from backend.auth.deps import get_current_user
from backend.db.models import Agent, Run, Step, User
from backend.db.session import get_db

router = APIRouter(prefix="/runs", tags=["approval"])


def _owned_run(run_id: int, user: User, db: Session) -> Run:
    run = db.get(Run, run_id)
    agent = db.get(Agent, run.agent_id) if run else None
    if run is None or agent is None or agent.user_id != user.id:
        raise HTTPException(404, "Run not found")
    return run


def _answer(run_id: int, step_id: int, approved: bool, user: User, db: Session):
    run = _owned_run(run_id, user, db)
    step = db.get(Step, step_id)
    if step is None or step.run_id != run.id:
        raise HTTPException(404, "Step not found")
    try:
        step = service.decide_step(db, run, step, approved)
    except service.ApprovalError as e:
        raise HTTPException(409, str(e))
    return {"ok": True, "step_id": step.id, "status": step.status, "run_status": run.status}


@router.get("/{run_id}/approvals")
def pending_approvals(run_id: int, user: User = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    run = _owned_run(run_id, user, db)
    return [{"step_id": s.id, "tool": s.tool, "input": s.input}
            for s in service.pending_steps(db, run.id)]


@router.post("/{run_id}/steps/{step_id}/approve")
def approve(run_id: int, step_id: int, user: User = Depends(get_current_user),
            db: Session = Depends(get_db)):
    return _answer(run_id, step_id, True, user, db)


@router.post("/{run_id}/steps/{step_id}/reject")
def reject(run_id: int, step_id: int, user: User = Depends(get_current_user),
           db: Session = Depends(get_db)):
    return _answer(run_id, step_id, False, user, db)
