from fastapi import FastAPI
from backend.rag.router import router as rag_router
from backend.memory.router import router as memory_router
from backend.metrics.router import router as metrics_router


app = FastAPI(title="AgentOS")
app.include_router(rag_router)
app.include_router(memory_router)
app.include_router(metrics_router)

@app.get("/health")
def health():
    return {"status": "ok"}