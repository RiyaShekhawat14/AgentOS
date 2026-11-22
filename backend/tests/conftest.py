import sys
import types

import pytest

# The embedding model is heavy and not needed for these tests.
try:
    import sentence_transformers  # noqa: F401
except ImportError:
    stub = types.ModuleType("sentence_transformers")
    stub.SentenceTransformer = object
    sys.modules["sentence_transformers"] = stub

from fastapi.testclient import TestClient
from pgvector.sqlalchemy import Vector
from sqlalchemy import create_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.db import models  # noqa: F401  (registers tables)
from backend.db.session import Base, get_db
from backend.main import app


@compiles(Vector, "sqlite")
def _vector_as_text_on_sqlite(type_, compiler, **kw):
    return "TEXT"  # lets the tests create the embeddings table without Postgres


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def client(db_session):
    def _override():
        yield db_session

    app.dependency_overrides[get_db] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()


def make_user(client, email="riya@example.com", name="Riya"):
    """Register a user and return the Authorization header for them."""
    res = client.post("/auth/register",
                      json={"email": email, "name": name, "password": "secret1"})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['token']}"}


@pytest.fixture()
def auth(client):
    return make_user(client)
