"""Tests for the knowledge (RAG) and memory APIs: login is required and users are isolated."""
import pytest

from backend.db import models
from backend.tests.conftest import make_user


@pytest.fixture()
def fake_embedding(monkeypatch):
    # The real model is heavy; return fixed 384-number vectors instead.
    monkeypatch.setattr("backend.rag.ingest.embed", lambda texts: [[0.1] * 384 for _ in texts])


@pytest.fixture()
def fake_memory_db(monkeypatch, db_session):
    # memory.service opens its own session; point it at the test database.
    monkeypatch.setattr("backend.memory.service.SessionLocal", lambda: _Keep(db_session))


class _Keep:
    """Wraps the shared test session so service code can call close() without closing it."""
    def __init__(self, s): self._s = s
    def __getattr__(self, name): return getattr(self._s, name)
    def close(self): pass


def _agent(client, headers, name="A"):
    res = client.post("/agents", json={"name": name, "tools": ["calculator"]}, headers=headers)
    assert res.status_code == 201, res.text
    return res.json()["id"]


def test_login_required(client):
    assert client.get("/agents/1/knowledge").status_code == 401
    assert client.post("/agents/1/knowledge", files={"file": ("a.txt", b"hi")}).status_code == 401
    assert client.get("/agents/1/memory").status_code == 401
    assert client.post("/agents/1/memory", json={"kind": "long", "content": "x"}).status_code == 401
    assert client.delete("/memory/1").status_code == 401


def test_upload_list_delete_document(client, auth, fake_embedding):
    aid = _agent(client, auth)
    text = ("Quarterly revenue grew twelve percent. " * 30).encode()
    res = client.post(f"/agents/{aid}/knowledge", files={"file": ("report.txt", text)}, headers=auth)
    assert res.status_code == 201, res.text
    assert res.json()["chunks"] >= 1

    docs = client.get(f"/agents/{aid}/knowledge", headers=auth).json()
    assert [d["filename"] for d in docs] == ["report.txt"]
    assert docs[0]["chunks"] >= 1

    assert client.delete(f"/agents/{aid}/knowledge/{docs[0]['id']}", headers=auth).status_code == 200
    assert client.get(f"/agents/{aid}/knowledge", headers=auth).json() == []


def test_upload_rejects_bad_files(client, auth, fake_embedding):
    aid = _agent(client, auth)
    r = client.post(f"/agents/{aid}/knowledge", files={"file": ("virus.exe", b"x")}, headers=auth)
    assert r.status_code == 400
    r = client.post(f"/agents/{aid}/knowledge", files={"file": ("empty.txt", b"   ")}, headers=auth)
    assert r.status_code == 400
    r = client.post(f"/agents/{aid}/knowledge", files={"file": ("bad.pdf", b"not a pdf")}, headers=auth)
    assert r.status_code == 400


def test_other_user_cannot_touch_my_knowledge(client, auth, fake_embedding):
    aid = _agent(client, auth)
    client.post(f"/agents/{aid}/knowledge", files={"file": ("a.txt", b"secret " * 50)}, headers=auth)
    doc_id = client.get(f"/agents/{aid}/knowledge", headers=auth).json()[0]["id"]

    other = make_user(client, email="other@example.com", name="Other")
    assert client.get(f"/agents/{aid}/knowledge", headers=other).status_code == 404
    assert client.get(f"/agents/{aid}/knowledge/search?q=secret", headers=other).status_code == 404
    assert client.delete(f"/agents/{aid}/knowledge/{doc_id}", headers=other).status_code == 404
    assert client.post(f"/agents/{aid}/knowledge", files={"file": ("b.txt", b"hack")},
                       headers=other).status_code == 404
    # and the owner's document is still there
    assert len(client.get(f"/agents/{aid}/knowledge", headers=auth).json()) == 1


def test_search_returns_hits(client, auth, monkeypatch):
    aid = _agent(client, auth)
    monkeypatch.setattr("backend.rag.router.retrieve",
                        lambda agent_id, q, k: [{"text": "t", "source": "s.txt", "score": 0.9}])
    res = client.get(f"/agents/{aid}/knowledge/search?q=hello", headers=auth)
    assert res.status_code == 200 and res.json()[0]["source"] == "s.txt"


def test_memory_add_list_filter_delete(client, auth, fake_memory_db):
    aid = _agent(client, auth)
    assert client.post(f"/agents/{aid}/memory", json={"kind": "long", "content": "Use INR"},
                       headers=auth).status_code == 201
    assert client.post(f"/agents/{aid}/memory", json={"kind": "short", "content": "Task one"},
                       headers=auth).status_code == 201
    allm = client.get(f"/agents/{aid}/memory", headers=auth).json()
    assert len(allm) == 2
    longm = client.get(f"/agents/{aid}/memory?kind=long", headers=auth).json()
    assert [m["content"] for m in longm] == ["Use INR"]
    assert client.delete(f"/memory/{longm[0]['id']}", headers=auth).status_code == 200
    assert len(client.get(f"/agents/{aid}/memory", headers=auth).json()) == 1


def test_memory_validation(client, auth, fake_memory_db):
    aid = _agent(client, auth)
    assert client.post(f"/agents/{aid}/memory", json={"kind": "weird", "content": "x"},
                       headers=auth).status_code == 400
    assert client.post(f"/agents/{aid}/memory", json={"kind": "long", "content": "   "},
                       headers=auth).status_code == 422


def test_other_user_cannot_touch_my_memory(client, auth, fake_memory_db):
    aid = _agent(client, auth)
    client.post(f"/agents/{aid}/memory", json={"kind": "long", "content": "private"}, headers=auth)
    mem_id = client.get(f"/agents/{aid}/memory", headers=auth).json()[0]["id"]

    other = make_user(client, email="other@example.com", name="Other")
    assert client.get(f"/agents/{aid}/memory", headers=other).status_code == 404
    assert client.post(f"/agents/{aid}/memory", json={"kind": "long", "content": "x"},
                       headers=other).status_code == 404
    assert client.delete(f"/memory/{mem_id}", headers=other).status_code == 404
    assert len(client.get(f"/agents/{aid}/memory", headers=auth).json()) == 1
