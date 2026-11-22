from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.agents.schemas import AgentIn, AgentOut
from backend.auth.deps import get_current_user
from backend.db.models import Agent, Document, Embedding, Memory, Run, Step, User
from backend.db.session import get_db

router = APIRouter(prefix="/agents", tags=["agents"])


def _get_owned_agent(db: Session, agent_id: int, user: User) -> Agent:
    """Return the agent if it belongs to this user, else 404 (do not reveal it exists)."""
    agent = db.get(Agent, agent_id)
    if agent is None or agent.user_id != user.id:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.post("", response_model=AgentOut, status_code=201)
def create_agent(body: AgentIn, db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    agent = Agent(user_id=user.id, **body.model_dump())
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


@router.get("", response_model=list[AgentOut])
def list_agents(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.scalars(
        select(Agent).where(Agent.user_id == user.id).order_by(Agent.id)
    ).all()


@router.get("/{agent_id}", response_model=AgentOut)
def get_agent(agent_id: int, db: Session = Depends(get_db),
              user: User = Depends(get_current_user)):
    return _get_owned_agent(db, agent_id, user)


@router.put("/{agent_id}", response_model=AgentOut)
def update_agent(agent_id: int, body: AgentIn, db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    agent = _get_owned_agent(db, agent_id, user)
    for field, value in body.model_dump().items():
        setattr(agent, field, value)
    db.commit()
    db.refresh(agent)
    return agent


@router.delete("/{agent_id}")
def delete_agent(agent_id: int, db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    agent = _get_owned_agent(db, agent_id, user)
    # Child rows have foreign keys to the agent, so remove them first.
    doc_ids = select(Document.id).where(Document.agent_id == agent.id)
    run_ids = select(Run.id).where(Run.agent_id == agent.id)
    db.execute(delete(Embedding).where(Embedding.doc_id.in_(doc_ids)))
    db.execute(delete(Document).where(Document.agent_id == agent.id))
    db.execute(delete(Memory).where(Memory.agent_id == agent.id))
    db.execute(delete(Step).where(Step.run_id.in_(run_ids)))
    db.execute(delete(Run).where(Run.agent_id == agent.id))
    db.delete(agent)
    db.commit()
    return {"ok": True}
