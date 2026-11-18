from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.memory import service

router = APIRouter(tags=["memory"])

class MemoryIn(BaseModel):
    kind: str
    content: str

@router.get("/agents/{agent_id}/memory")
def list_memory(agent_id: int, kind: str | None = None):
    return service.get(agent_id, kind)

@router.post("/agents/{agent_id}/memory")
def add_memory(agent_id: int, body: MemoryIn):
    try:
        service.save(agent_id, body.kind, body.content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True}

@router.delete("/memory/{memory_id}")
def remove_memory(memory_id: int):
    if not service.delete_memory(memory_id):
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"ok": True}