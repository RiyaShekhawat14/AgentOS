from dotenv import load_dotenv
load_dotenv()

import threading
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.rag.router import router as rag_router
from backend.memory.router import router as memory_router
from backend.metrics.router import router as metrics_router
from backend.auth.router import router as auth_router
from backend.agents.router import router as agents_router
from backend.tools.router import router as files_router
from backend.approval.router import router as approval_router
from backend.runs.router import router as runs_router
from backend.scheduler.router import router as schedule_router
from backend.scheduler import service as scheduler_service
from backend.db import models  # noqa: F401  (registers the tables)
from backend.db.session import Base, engine
from fastapi.middleware.cors import CORSMiddleware

def _prepare_database_and_scheduler() -> None:
    """Create any new tables and start the scheduler.

    This runs in the background on purpose: if the database is slow or still starting,
    the API must still come up (so /docs and /health work) instead of waiting for it.
    """
    for _ in range(12):
        try:
            Base.metadata.create_all(engine)  # creates any table that is new since the last start
            scheduler_service.start()
            return
        except Exception as e:
            print(f"Database not ready yet ({type(e).__name__}). Trying again in 5 seconds...")
            time.sleep(5)
    print("Could not start the scheduler. Start the database, then restart the backend.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    threading.Thread(target=_prepare_database_and_scheduler, daemon=True, name="startup").start()
    yield
    scheduler_service.stop()


# Initialize FastAPI application
app = FastAPI(title="AgentOS", lifespan=lifespan)
from fastapi.middleware.cors import CORSMiddleware

# The browser only lets the website call this API if the website's address is allowed here.
# Any port on localhost / 127.0.0.1 is allowed, so it still works if the frontend starts on 3001.

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Register all routers
app.include_router(auth_router)
app.include_router(agents_router)
app.include_router(files_router)
app.include_router(approval_router)
app.include_router(runs_router)
app.include_router(rag_router)
app.include_router(memory_router)
app.include_router(metrics_router)
app.include_router(schedule_router)

@app.get("/health")
def health():
    return {"status": "ok"}