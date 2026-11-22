from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from backend.auth.deps import get_current_user, get_owned_agent
from backend.db.models import Document, Embedding, User
from backend.db.session import get_db
from backend.rag.ingest import ingest_document
from backend.rag.service import retrieve

router = APIRouter(prefix="/agents", tags=["knowledge"])

ALLOWED_EXTENSIONS = (".pdf", ".txt", ".csv", ".md")
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB


# A plain "def" (not "async def") on purpose: embedding is slow, and FastAPI runs
# plain functions in a worker thread so the rest of the API stays responsive.
@router.post("/{agent_id}/knowledge", status_code=201)
def upload_knowledge(agent_id: int, file: UploadFile = File(...),
                     db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    get_owned_agent(db, agent_id, user)
    name = file.filename or ""
    if not name.lower().endswith(ALLOWED_EXTENSIONS):
        raise HTTPException(status_code=400,
                            detail="Allowed file types: " + ", ".join(ALLOWED_EXTENSIONS))
    data = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File is larger than 10 MB")
    try:
        return ingest_document(db, agent_id, name, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{agent_id}/knowledge")
def list_knowledge(agent_id: int, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    get_owned_agent(db, agent_id, user)
    rows = db.execute(
        select(Document.id, Document.filename, func.count(Embedding.id))
        .outerjoin(Embedding, Embedding.doc_id == Document.id)
        .where(Document.agent_id == agent_id)
        .group_by(Document.id, Document.filename)
        .order_by(Document.id)
    ).all()
    return [{"id": i, "filename": f, "chunks": c} for i, f, c in rows]


@router.delete("/{agent_id}/knowledge/{doc_id}")
def delete_knowledge(agent_id: int, doc_id: int, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    get_owned_agent(db, agent_id, user)
    doc = db.get(Document, doc_id)
    if doc is None or doc.agent_id != agent_id:
        raise HTTPException(status_code=404, detail="Document not found")
    db.execute(delete(Embedding).where(Embedding.doc_id == doc.id))
    db.delete(doc)
    db.commit()
    return {"ok": True}


@router.get("/{agent_id}/knowledge/search")
def search_knowledge(agent_id: int, q: str, k: int = 4, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    get_owned_agent(db, agent_id, user)
    return retrieve(agent_id, q, max(1, min(k, 10)))
