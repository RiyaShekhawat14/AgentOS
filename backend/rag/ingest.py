from io import BytesIO
from pypdf import PdfReader
from sqlalchemy.orm import Session
from backend.db.models import Document, Embedding
from backend.rag.chunker import chunk_text
from backend.rag.embedder import embed

def extract_text(filename: str, data: bytes) -> str:
    if filename.lower().endswith(".pdf"):
        reader = PdfReader(BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return data.decode("utf-8", errors="ignore")  # .txt, .csv, .md

def ingest_document(db: Session, agent_id: int, filename: str, data: bytes) -> dict:
    text = extract_text(filename, data)
    chunks = chunk_text(text)
    if not chunks:
        raise ValueError("No readable text found in this file")

    doc = Document(agent_id=agent_id, filename=filename)
    db.add(doc)
    db.flush()  # gives doc.id

    vectors = embed(chunks)
    for chunk, vec in zip(chunks, vectors):
        db.add(Embedding(doc_id=doc.id, chunk_text=chunk, vector=vec))
    db.commit()
    return {"document_id": doc.id, "filename": filename, "chunks": len(chunks)}