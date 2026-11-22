import time
from typing import Callable

from sqlalchemy.orm import Session

from backend.db.models import Run, Step

WAITING = "waiting_approval"
APPROVED = "approved"
REJECTED = "rejected"

DEFAULT_TIMEOUT = 600  # seconds a human has to answer
POLL_SECONDS = 1.0


class ApprovalError(Exception):
    """The step cannot be approved or rejected (already decided, wrong run...)."""


def request_approval(db: Session, run: Run, step: Step) -> Step:
    """Pause the run and mark the tool step as waiting for a human."""
    step.status = WAITING
    run.status = WAITING
    db.commit()
    return step


def pending_steps(db: Session, run_id: int) -> list[Step]:
    return (db.query(Step)
            .filter(Step.run_id == run_id, Step.status == WAITING)
            .order_by(Step.id).all())


def decide_step(db: Session, run: Run, step: Step, approved: bool) -> Step:
    """Record the human's answer and let the run continue."""
    if step.run_id != run.id:
        raise ApprovalError("This step does not belong to the run.")
    if step.status != WAITING:
        raise ApprovalError("This step is not waiting for approval.")
    step.status = APPROVED if approved else REJECTED
    db.flush()
    if run.status == WAITING and not pending_steps(db, run.id):
        run.status = "running"  # nothing else is waiting, so the run can continue
    db.commit()
    return step


def wait_for_decision(session_factory: Callable[[], Session], step_id: int,
                      timeout: float = DEFAULT_TIMEOUT, poll: float = POLL_SECONDS,
                      sleep: Callable[[float], None] = time.sleep) -> str:
    """Block (in the run's worker thread) until a human answers.

    Returns "approved", "rejected", "timeout" (nobody answered in time, step is
    marked rejected) or "cancelled" (the run was stopped while waiting).
    A fresh DB session is used for every check so we always see the latest data.
    """
    waited = 0.0
    while True:
        db = session_factory()
        try:
            step = db.get(Step, step_id)
            if step is None:
                return "cancelled"
            if step.status in (APPROVED, REJECTED):
                return step.status
            run = db.get(Run, step.run_id)
            if run is None or run.status not in (WAITING, "running"):
                return "cancelled"  # failed / stopped by the user
            if waited >= timeout:
                step.status = REJECTED
                step.output = {"error": "No one answered in time, so the step was rejected."}
                db.commit()
                return "timeout"
        finally:
            db.close()
        sleep(poll)
        waited += poll
