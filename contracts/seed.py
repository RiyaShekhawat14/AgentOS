
from datetime import datetime, timedelta
from sqlalchemy import text
from backend.db.session import engine, SessionLocal, Base
from backend.db import models  # noqa: registers tables

with engine.begin() as conn:
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

Base.metadata.create_all(engine)

db = SessionLocal()

try:
    user = db.get(models.User, 1)

    if not user:
        user = models.User(
            id=1,
            email="demo@agentos.dev",
            name="Demo User"
        )
        db.add(user)
        db.flush()  # Save the user before creating the agent

    agent = db.get(models.Agent, 1)

    if not agent:
        agent = models.Agent(
            id=1,
            user_id=1,
            name="Sales Analyst",
            instructions="Report KPIs in INR",
            tools=["files", "calculator"],
            permissions={"code": "ask"}
        )
        db.add(agent)
        db.flush()

        for i, status in enumerate(
            ["done", "done", "failed", "done", "waiting_approval"]
        ):
            start = datetime.utcnow() - timedelta(days=i)

            run = models.Run(
                agent_id=1,
                task=f"Sample task {i+1}",
                status=status,
                started=start,
                ended=start + timedelta(seconds=38)
            )
            db.add(run)
            db.flush()

            db.add(
                models.Step(
                    run_id=run.id,
                    type="tool",
                    tool="read_csv",
                    ms=420
                )
            )

    db.commit()
    print("Seed done")

except Exception:
    db.rollback()
    raise

finally:
    db.close()
