from sqlalchemy import select

from backend.db.models import Agent, Document, Embedding, Memory, Run, Step
from backend.tests.conftest import make_user

BODY = {
    "name": "Sales Analyst",
    "instructions": "Always report KPIs in INR",
    "tools": ["calculator", "csv_reader"],
    "permissions": {"code": "ask"},
}


def test_requires_login(client):
    assert client.get("/agents").status_code == 401
    assert client.post("/agents", json=BODY).status_code == 401


def test_create_and_get(client, auth):
    res = client.post("/agents", json=BODY, headers=auth)
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Sales Analyst"
    assert data["tools"] == ["calculator", "csv_reader"]
    assert data["permissions"] == {"code": "ask"}
    assert data["schedule"] is None

    got = client.get(f"/agents/{data['id']}", headers=auth)
    assert got.status_code == 200 and got.json() == data


def test_defaults_and_name_trimmed(client, auth):
    res = client.post("/agents", json={"name": "  Helper  "}, headers=auth)
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Helper"
    assert data["instructions"] == "" and data["tools"] == [] and data["permissions"] == {}


def test_duplicate_tools_removed(client, auth):
    res = client.post("/agents", json={"name": "A", "tools": ["calculator", "calculator"]},
                      headers=auth)
    assert res.json()["tools"] == ["calculator"]


def test_validation_errors(client, auth):
    assert client.post("/agents", json={"name": "   "}, headers=auth).status_code == 422
    assert client.post("/agents", json={"name": ""}, headers=auth).status_code == 422
    assert client.post("/agents", json={"name": "A", "tools": ["hack"]},
                       headers=auth).status_code == 422
    assert client.post("/agents", json={"name": "A", "permissions": {"code": "maybe"}},
                       headers=auth).status_code == 422
    assert client.post("/agents", json={"name": "A", "permissions": {"hack": "auto"}},
                       headers=auth).status_code == 422
    assert client.post("/agents", json={"name": "x" * 101}, headers=auth).status_code == 422


def test_list_only_my_agents(client, auth):
    other = make_user(client, "khushi@example.com", "Khushi")
    client.post("/agents", json={"name": "Mine"}, headers=auth)
    client.post("/agents", json={"name": "Theirs"}, headers=other)
    names = [a["name"] for a in client.get("/agents", headers=auth).json()]
    assert names == ["Mine"]


def test_cannot_touch_someone_elses_agent(client, auth):
    other = make_user(client, "khushi@example.com", "Khushi")
    agent_id = client.post("/agents", json={"name": "Theirs"}, headers=other).json()["id"]
    assert client.get(f"/agents/{agent_id}", headers=auth).status_code == 404
    assert client.put(f"/agents/{agent_id}", json={"name": "Hacked"},
                      headers=auth).status_code == 404
    assert client.delete(f"/agents/{agent_id}", headers=auth).status_code == 404
    # still there and unchanged for the real owner
    assert client.get(f"/agents/{agent_id}", headers=other).json()["name"] == "Theirs"


def test_missing_agent_is_404(client, auth):
    assert client.get("/agents/999", headers=auth).status_code == 404


def test_update(client, auth):
    agent_id = client.post("/agents", json=BODY, headers=auth).json()["id"]
    new = {"name": "Renamed", "instructions": "x", "tools": ["web_search"],
           "permissions": {"web_search": "auto"}, "schedule": "Every Monday 9:00"}
    res = client.put(f"/agents/{agent_id}", json=new, headers=auth)
    assert res.status_code == 200
    assert res.json() == {"id": agent_id, **new}
    assert client.put(f"/agents/{agent_id}", json={"name": "A", "tools": ["nope"]},
                      headers=auth).status_code == 422


def test_delete_removes_agent_and_related_rows(client, auth, db_session):
    agent_id = client.post("/agents", json=BODY, headers=auth).json()["id"]
    other_id = client.post("/agents", json={"name": "Keep me"}, headers=auth).json()["id"]
    for aid in (agent_id, other_id):
        run = Run(agent_id=aid, task="t")
        db_session.add(run)
        db_session.flush()
        db_session.add(Step(run_id=run.id, type="tool", tool="calculator"))
        db_session.add(Memory(agent_id=aid, kind="long", content="fact"))
        doc = Document(agent_id=aid, filename="a.txt")
        db_session.add(doc)
        db_session.flush()
        db_session.add(Embedding(doc_id=doc.id, chunk_text="c", vector=[0.0]))
    db_session.commit()

    res = client.delete(f"/agents/{agent_id}", headers=auth)
    assert res.status_code == 200 and res.json() == {"ok": True}
    assert client.get(f"/agents/{agent_id}", headers=auth).status_code == 404

    for model, col in ((Run, Run.agent_id), (Memory, Memory.agent_id),
                       (Document, Document.agent_id)):
        left = db_session.scalars(select(model)).all()
        assert [getattr(r, col.key) for r in left] == [other_id]
    assert db_session.scalar(select(Agent).where(Agent.id == other_id)) is not None
    assert len(db_session.scalars(select(Step)).all()) == 1
    assert len(db_session.scalars(select(Embedding)).all()) == 1
