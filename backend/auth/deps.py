from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from backend.db.session import get_db
from backend.db.models import Agent, User
from backend.auth.security import decode_token

bearer = HTTPBearer(auto_error=False)

def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if creds is None:
        raise HTTPException(status_code=401, detail="Not logged in")
    user_id = decode_token(creds.credentials)
    user = db.get(User, user_id) if user_id else None
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user

def get_owned_agent(db: Session, agent_id: int, user: User) -> Agent:
    """Return the agent only if it belongs to this user. Otherwise answer 404,
    so nobody can even find out that another user's agent exists."""
    agent = db.get(Agent, agent_id)
    if agent is None or agent.user_id != user.id:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent
