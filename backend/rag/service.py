# backend/rag/service.py
def retrieve(agent_id: int, query: str, k: int = 4) -> list[dict]:
    """STUB: returns fixed sample chunks. Real pgvector search replaces this later."""
    return [
        {"text": "Sample chunk 1: Q3 revenue grew 12%.", "source": "sample.pdf", "score": 0.9},
        {"text": "Sample chunk 2: Top product is Widget A.", "source": "sample.pdf", "score": 0.8},
    ][:k]