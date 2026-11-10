from fastapi import FastAPI
from backend.rag.router import router as rag_router

app = FastAPI(title="AgentOS")
app.include_router(rag_router)

@app.get("/health")
def health():
    return {"status": "ok"}