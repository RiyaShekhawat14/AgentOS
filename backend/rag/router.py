from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from backend.db.session import get_db
from backend.db.models import Agent
from backend.rag.ingest import ingest_document

router = APIRouter(prefix="/agents", tags=["knowledge"])

@router.post("/{agent_id}/knowledge")
async def upload_knowledge(agent_id: int, file: UploadFile = File(...),
                           db: Session = Depends(get_db)):
    if db.get(Agent, agent_id) is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    data = await file.read()
    try:
        return ingest_document(db, agent_id, file.filename, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))