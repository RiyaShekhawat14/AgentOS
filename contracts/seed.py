"""Creates the tables and some sample data. Safe to run again at any time.

    python -m contracts.seed

Demo login:  demo@agentos.dev  /  demo123
"""
from datetime import datetime, timedelta

from sqlalchemy import text

from backend.auth.security import hash_password
from backend.db import models  # noqa: F401  (registers the tables)
from backend.db.session import Base, SessionLocal, engine

DEMO_PASSWORD = "demo123"

with engine.begin() as conn:
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

Base.metadata.create_all(engine)  # also creates any table added later (e.g. schedules)

db = SessionLocal()

try:
    user = db.get(models.User, 1)
    if not user:
        user = models.User(id=1, email="demo@agentos.dev", name="Demo User")
        db.add(user)
        db.flush()
    if not user.password_hash:  # lets you log in as the demo user
        user.password_hash = hash_password(DEMO_PASSWORD)

    agent = db.get(models.Agent, 1)
    if not agent:
        agent = models.Agent(
            id=1,
            user_id=1,
            name="Sales Analyst",
            instructions="Report KPIs in INR",
            tools=["csv_reader", "calculator"],
            permissions={"code": "ask"},
        )
        db.add(agent)
        db.flush()

        for i, status in enumerate(["done", "done", "failed", "done", "waiting_approval"]):
            start = datetime.utcnow() - timedelta(days=i)
            run = models.Run(
                agent_id=1,
                task=f"Sample task {i + 1}",
                status=status,
                started=start,
                ended=start + timedelta(seconds=38),
            )
            db.add(run)
            db.flush()
            db.add(models.Step(run_id=run.id, type="tool", tool="csv_reader", ms=420))
    else:
        # older seed data used "files" / "read_csv"; the real tool is called "csv_reader"
        agent.tools = ["csv_reader" if t == "files" else t for t in (agent.tools or [])]
        db.execute(text("UPDATE steps SET tool = 'csv_reader' WHERE tool = 'read_csv'"))

    db.commit()
except Exception:
    db.rollback()
    raise
finally:
    db.close()

# We gave some rows fixed ids (1, 2...). Move the id counters past them, or the next
# new user or agent would try to reuse id 1 and fail.
with engine.begin() as conn:
    for table in ("users", "agents", "runs", "steps"):
        conn.execute(text(
            f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
            f"COALESCE((SELECT MAX(id) FROM {table}), 1))"
        ))

print("Seed done. Demo login: demo@agentos.dev / " + DEMO_PASSWORD)
