
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI

from backend.rag.router import router as rag_router
from backend.memory.router import router as memory_router
from backend.metrics.router import router as metrics_router
from backend.auth.router import router as auth_router

# Initialize FastAPI application
app = FastAPI(title="AgentOS")
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all routers
app.include_router(auth_router)
app.include_router(rag_router)
app.include_router(memory_router)
app.include_router(metrics_router)

@app.get("/health")
def health():
    return {"status": "ok"}
