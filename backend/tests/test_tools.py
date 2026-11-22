import pytest

from backend.tools import web_search
from backend.tools.registry import TOOLS, describe, run_tool
from backend.tests.conftest import make_user

SALES = (
    "Region,Product,Amount\n"
    "North,Pen,100\nNorth,Book,300\nSouth,Pen,200\nSouth,Book,250\n"
    "East,Pen,150\nEast,Book,5000\n"
)


@pytest.fixture(autouse=True)
def storage(tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture()
def csv_file(storage):
    folder = storage / "agent_1"
    folder.mkdir()
    (folder / "Sales.csv").write_text(SALES)


def test_registry_names_match_agent_tools():
    from backend.agents.schemas import ALLOWED_TOOLS
    assert set(TOOLS) == set(ALLOWED_TOOLS)
    assert [d["name"] for d in describe(["calculator", "nope"])] == ["calculator"]


# ---- calculator ----
@pytest.mark.parametrize("expr,expected", [
    ("2 + 3 * 4", 14), ("(1200 * 0.18) + 50", 266.0), ("2 ** 10", 1024),
    ("mean([3, 5, 10])", 6.0), ("sqrt(16) + max(1, 7)", 11.0), ("-5 % 3", 1),
])
def test_calculator_ok(expr, expected):
    out = run_tool("calculator", {"expression": expr}, 1)
    assert out == {"ok": True, "result": {"expression": expr, "result": expected}}


@pytest.mark.parametrize("expr", [
    "", "1 / 0", "__import__('os').system('echo hi')", "open('x')", "2 ** 100000",
    "abs.__class__", "x + 1", "1 +", "'a' * 5", "9" * 600,
])
def test_calculator_rejects_bad_input(expr):
    out = run_tool("calculator", {"expression": expr}, 1)
    assert out["ok"] is False and out["error"]


# ---- csv reader ----
def test_csv_describe(csv_file):
    out = run_tool("csv_reader", {"file": "Sales.csv"}, 1)["result"]
    assert out["rows"] == 6
    amount = next(c for c in out["columns"] if c["name"] == "Amount")
    assert amount["type"] == "number" and amount["max"] == 5000 and amount["sum"] == 6000
    assert next(c for c in out["columns"] if c["name"] == "Region")["type"] == "text"


def test_csv_head_and_aggregate(csv_file):
    head = run_tool("csv_reader", {"file": "Sales.csv", "action": "head", "n": 2}, 1)["result"]
    assert len(head["rows"]) == 2 and head["columns"] == ["Region", "Product", "Amount"]
    agg = run_tool("csv_reader", {"file": "Sales.csv", "action": "aggregate",
                                  "column": "amount", "group_by": "Region"}, 1)["result"]
    assert agg["groups"][0] == {"group": "East", "value": 5150.0}
    cnt = run_tool("csv_reader", {"file": "Sales.csv", "action": "aggregate", "agg": "count",
                                  "group_by": "Product"}, 1)["result"]
    assert {g["group"]: g["value"] for g in cnt["groups"]} == {"Pen": 3, "Book": 3}


def test_csv_anomalies(csv_file):
    out = run_tool("csv_reader", {"file": "Sales.csv", "action": "anomalies",
                                  "column": "Amount"}, 1)["result"]
    assert out["anomaly_count"] == 1 and out["anomalies"][0]["value"] == 5000


def test_csv_errors(csv_file):
    assert "not found" in run_tool("csv_reader", {"file": "nope.csv"}, 1)["error"]
    assert "Available CSV files" in run_tool("csv_reader", {"file": "nope.csv"}, 1)["error"]
    assert "Column" in run_tool("csv_reader", {"file": "Sales.csv", "action": "aggregate",
                                               "column": "Missing"}, 1)["error"]
    assert not run_tool("csv_reader", {"file": "Sales.csv", "action": "boom"}, 1)["ok"]


def test_csv_cannot_leave_agent_folder(storage, csv_file):
    (storage / "secret.csv").write_text("a\n1\n")
    out = run_tool("csv_reader", {"file": "../secret.csv"}, 1)
    assert out["ok"] is False  # only the file name is used, so the other folder is unreachable
    assert not run_tool("csv_reader", {"file": "Sales.csv"}, 2)["ok"]  # other agent has no files


# ---- web search ----
PAGE = """
<a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fa&amp;rut=1">First <b>hit</b></a>
<a class="result__snippet" href="x">About &amp; around <b>things</b></a>
<a class="result__a" href="https://example.org/b">Second</a>
<a class="result__snippet" href="x">Another snippet</a>
"""


def test_web_search_parses_results(monkeypatch):
    monkeypatch.setattr(web_search, "fetch_page", lambda q: PAGE)
    out = run_tool("web_search", {"query": "agents", "max_results": 1}, 1)["result"]
    assert out["results"] == [{"title": "First hit", "url": "https://example.com/a",
                               "snippet": "About & around things"}]
    both = run_tool("web_search", {"query": "agents"}, 1)["result"]["results"]
    assert [r["url"] for r in both] == ["https://example.com/a", "https://example.org/b"]


def test_web_search_errors(monkeypatch):
    assert not run_tool("web_search", {"query": " "}, 1)["ok"]
    monkeypatch.setattr(web_search, "fetch_page", lambda q: "<html></html>")
    assert "No results" in run_tool("web_search", {"query": "x"}, 1)["error"]

    def offline(q):
        raise OSError("no internet")
    monkeypatch.setattr(web_search, "fetch_page", offline)
    assert "not available" in run_tool("web_search", {"query": "x"}, 1)["error"]


# ---- code sandbox ----
def test_code_runs_and_prints():
    out = run_tool("code", {"code": "print(sum(range(5)))"}, 1)
    assert out["ok"] and out["result"]["output"].strip() == "10"


def test_code_error_timeout_and_empty(monkeypatch):
    bad = run_tool("code", {"code": "1/0"}, 1)
    assert not bad["ok"] and "ZeroDivisionError" in bad["error"]
    from backend.tools import code
    monkeypatch.setattr(code, "TIMEOUT_SECONDS", 1)
    slow = run_tool("code", {"code": "while True: pass"}, 1)
    assert not slow["ok"] and ("longer than" in slow["error"] or "failed" in slow["error"])
    assert not run_tool("code", {"code": ""}, 1)["ok"]


def test_code_has_no_secrets_and_clean_folder(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "top-secret")
    out = run_tool("code", {"code": "import os; print(os.environ.get('JWT_SECRET'), os.listdir('.'))"}, 1)
    assert out["result"]["output"].strip() == "None []"


# ---- unknown tool ----
def test_unknown_tool_and_bad_args():
    assert "Unknown tool" in run_tool("hack", {}, 1)["error"]
    assert not run_tool("calculator", "2+2", 1)["ok"]


# ---- upload API ----
def _agent(client, auth):
    return client.post("/agents", json={"name": "A", "tools": ["csv_reader"]}, headers=auth).json()["id"]


def test_upload_list_delete(client, auth):
    aid = _agent(client, auth)
    assert client.get(f"/agents/{aid}/files").status_code == 401
    up = client.post(f"/agents/{aid}/files", headers=auth,
                     files={"file": ("../My Sales!.csv", SALES, "text/csv")})
    assert up.status_code == 201 and up.json()["name"] == "My Sales_.csv"
    assert client.get(f"/agents/{aid}/files", headers=auth).json()[0]["name"] == "My Sales_.csv"
    out = run_tool("csv_reader", {"file": "My Sales_.csv"}, aid)
    assert out["ok"] and out["result"]["rows"] == 6
    assert client.delete(f"/agents/{aid}/files/My Sales_.csv", headers=auth).json() == {"ok": True}
    assert client.get(f"/agents/{aid}/files", headers=auth).json() == []
    assert client.delete(f"/agents/{aid}/files/My Sales_.csv", headers=auth).status_code == 404


def test_upload_rules_and_ownership(client, auth):
    aid = _agent(client, auth)
    assert client.post(f"/agents/{aid}/files", headers=auth,
                       files={"file": ("a.exe", b"x")}).status_code == 400
    big = b"a,b\n" + b"1,2\n" * (2 * 1024 * 1024)
    assert client.post(f"/agents/{aid}/files", headers=auth,
                       files={"file": ("big.csv", big)}).status_code == 413
    other = make_user(client, email="khushi@example.com", name="Khushi")
    assert client.get(f"/agents/{aid}/files", headers=other).status_code == 404
    assert client.post(f"/agents/{aid}/files", headers=other,
                       files={"file": ("a.csv", SALES)}).status_code == 404
    assert client.get("/agents/999/files", headers=auth).status_code == 404
