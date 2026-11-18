from sqlalchemy import select, delete
from backend.db.session import SessionLocal
from backend.db.models import Memory

MAX_SHORT = 20  # keep only the newest 20 short-term memories per agent

def save(agent_id: int, kind: str, content: str) -> None:
    if kind not in ("short", "long"):
        raise ValueError("kind must be 'short' or 'long'")
    db = SessionLocal()
    try:
        db.add(Memory(agent_id=agent_id, kind=kind, content=content))
        db.commit()
        if kind == "short":
            keep = db.scalars(
                select(Memory.id).where(Memory.agent_id == agent_id, Memory.kind == "short")
                .order_by(Memory.id.desc()).limit(MAX_SHORT)
            ).all()
            db.execute(delete(Memory).where(
                Memory.agent_id == agent_id, Memory.kind == "short", Memory.id.not_in(keep)))
            db.commit()
    finally:
        db.close()

def get(agent_id: int, kind: str | None = None) -> list[dict]:
    db = SessionLocal()
    try:
        q = select(Memory).where(Memory.agent_id == agent_id)
        if kind:
            q = q.where(Memory.kind == kind)
        rows = db.scalars(q.order_by(Memory.id)).all()
        return [{"id": m.id, "kind": m.kind, "content": m.content} for m in rows]
    finally:
        db.close()

def delete_memory(memory_id: int) -> bool:
    db = SessionLocal()
    try:
        m = db.get(Memory, memory_id)
        if m is None:
            return False
        db.delete(m)
        db.commit()
        return True
    finally:
        db.close()