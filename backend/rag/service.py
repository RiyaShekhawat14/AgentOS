from sqlalchemy import select
from backend.db.session import SessionLocal
from backend.db.models import Document, Embedding
from backend.rag.embedder import embed

def retrieve(agent_id: int, query: str, k: int = 4) -> list[dict]:
    """Return the k chunks most similar to the query, from this agent's documents."""
    query_vec = embed([query])[0]
    db = SessionLocal()
    try:
        distance = Embedding.vector.cosine_distance(query_vec)
        rows = db.execute(
            select(Embedding.chunk_text, Document.filename, distance.label("dist"))
            .join(Document, Document.id == Embedding.doc_id)
            .where(Document.agent_id == agent_id)
            .order_by(distance)
            .limit(k)
        ).all()
        return [
            {"text": r.chunk_text, "source": r.filename, "score": round(1 - r.dist, 4)}
            for r in rows
        ]
    finally:
        db.close()