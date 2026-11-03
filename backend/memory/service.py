# backend/memory/service.py
_store: dict[int, list[dict]] = {}   # STUB: in-memory dictionary

def save(agent_id: int, kind: str, content: str) -> None:
    _store.setdefault(agent_id, []).append({"kind": kind, "content": content})

def get(agent_id: int, kind: str | None = None) -> list[dict]:
    items = _store.get(agent_id, [])
    return [m for m in items if kind is None or m["kind"] == kind]