from backend.db.models import User

def get_current_user() -> User:
    # TEMPORARY: always returns the demo user (id=1, created by seed.py)
    return User(id=1, email="demo@agentos.dev", name="Demo User")