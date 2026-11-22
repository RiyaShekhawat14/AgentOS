import re
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.auth.deps import get_current_user
from backend.db.models import Agent, User
from backend.db.session import get_db
from backend.tools.base import agent_data_dir

router = APIRouter(prefix="/agents/{agent_id}/files", tags=["files"])

MAX_FILE_BYTES = 5 * 1024 * 1024


def _owned_agent(agent_id: int, user: User, db: Session) -> Agent:
    agent = db.get(Agent, agent_id)
    if agent is None or agent.user_id != user.id:
        raise HTTPException(404, "Agent not found")
    return agent


def _safe_name(raw: str | None) -> str:
    name = re.sub(r"[^A-Za-z0-9._ -]", "_", Path(raw or "").name).strip()
    if not name.lower().endswith(".csv") or len(name) < 5:
        raise HTTPException(400, "Only .csv files are allowed")
    return name


@router.get("")
def list_files(agent_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _owned_agent(agent_id, user, db)
    folder = agent_data_dir(agent_id)
    files = sorted(folder.glob("*.csv")) if folder.is_dir() else []
    return [{"name": f.name, "size": f.stat().st_size} for f in files]


@router.post("", status_code=201)
async def upload_file(agent_id: int, file: UploadFile = File(...),
                      user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _owned_agent(agent_id, user, db)
    name = _safe_name(file.filename)
    data = await file.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES:
        raise HTTPException(413, "File is larger than 5 MB")
    folder = agent_data_dir(agent_id)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_bytes(data)
    return {"name": name, "size": len(data)}


@router.delete("/{name}")
def delete_file(agent_id: int, name: str, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    _owned_agent(agent_id, user, db)
    path = agent_data_dir(agent_id) / _safe_name(name)
    if not path.is_file():
        raise HTTPException(404, "File not found")
    path.unlink()
    return {"ok": True}
