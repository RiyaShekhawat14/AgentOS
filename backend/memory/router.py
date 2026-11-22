from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from backend.auth.deps import get_current_user, get_owned_agent
from backend.db.models import Memory, User
from backend.db.session import get_db
from backend.memory import service

router = APIRouter(tags=["memory"])


class MemoryIn(BaseModel):
    kind: str
    content: str

    @field_validator("content")
    @classmethod
    def content_ok(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Memory cannot be empty")
        if len(v) > 2000:
            raise ValueError("Memory is too long (max 2000 characters)")
        return v


@router.get("/agents/{agent_id}/memory")
def list_memory(agent_id: int, kind: str | None = None, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    get_owned_agent(db, agent_id, user)
    return service.get(agent_id, kind)


@router.post("/agents/{agent_id}/memory", status_code=201)
def add_memory(agent_id: int, body: MemoryIn, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    get_owned_agent(db, agent_id, user)
    try:
        service.save(agent_id, body.kind, body.content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True}


@router.delete("/memory/{memory_id}")
def remove_memory(memory_id: int, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    memory = db.get(Memory, memory_id)
    if memory is None:
        raise HTTPException(status_code=404, detail="Memory not found")
    get_owned_agent(db, memory.agent_id, user)  # 404 if it belongs to someone else
    service.delete_memory(memory_id)
    return {"ok": True}
