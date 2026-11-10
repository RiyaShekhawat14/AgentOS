from datetime import datetime
from sqlalchemy import String, Text, ForeignKey, JSON, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from backend.db.session import Base

EMBED_DIM = 384  # must match the embedding model you use

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)

class Agent(Base):
    __tablename__ = "agents"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(100))
    instructions: Mapped[str] = mapped_column(Text, default="")
    tools: Mapped[list] = mapped_column(JSON, default=list)
    permissions: Mapped[dict] = mapped_column(JSON, default=dict)  # {"code": "ask", "db": "blocked"}
    schedule: Mapped[str | None] = mapped_column(String(100), nullable=True)

class Run(Base):
    __tablename__ = "runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"))
    task: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="running")  # running/done/failed/waiting_approval
    started: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ended: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    steps: Mapped[list["Step"]] = relationship(back_populates="run")

class Step(Base):
    __tablename__ = "steps"
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"))
    type: Mapped[str] = mapped_column(String(30))        # plan / tool / observe
    tool: Mapped[str | None] = mapped_column(String(50), nullable=True)
    input: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    output: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="done")
    ms: Mapped[int] = mapped_column(Integer, default=0)
    run: Mapped[Run] = relationship(back_populates="steps")

class Document(Base):
    __tablename__ = "documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"))
    filename: Mapped[str] = mapped_column(String(255))

class Embedding(Base):
    __tablename__ = "embeddings"
    id: Mapped[int] = mapped_column(primary_key=True)
    doc_id: Mapped[int] = mapped_column(ForeignKey("documents.id"))
    chunk_text: Mapped[str] = mapped_column(Text)
    vector: Mapped[list[float]] = mapped_column(Vector(EMBED_DIM))

class Memory(Base):
    __tablename__ = "memories"
    id: Mapped[int] = mapped_column(primary_key=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"))
    kind: Mapped[str] = mapped_column(String(10))  # "short" or "long"
    content: Mapped[str] = mapped_column(Text)