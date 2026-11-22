"""Writes docs/API.md from the live FastAPI app, so the docs always match the code.

Run from the project root (with the backend venv active):
    python docs/generate_api_docs.py
"""
from collections import defaultdict
from pathlib import Path

from backend.main import app

METHODS = ("get", "post", "put", "patch", "delete")
spec = app.openapi()

groups: dict[str, list[tuple[str, str, str, bool]]] = defaultdict(list)
for path, ops in spec["paths"].items():
    for method in METHODS:
        op = ops.get(method)
        if not op:
            continue
        tag = (op.get("tags") or ["other"])[0]
        summary = op.get("summary", "")
        needs_login = bool(op.get("security"))
        groups[tag].append((method.upper(), path, summary, needs_login))

lines = [
    "# AgentOS API reference",
    "",
    "_Generated from the running app by `docs/generate_api_docs.py`. Do not edit by hand._",
    "",
    "Interactive version (try the endpoints in the browser): http://localhost:8000/docs",
    "",
    "**Login:** call `POST /auth/login`, copy the `token`, and send it with every request as "
    "`Authorization: Bearer <token>`. In `/docs` press the **Authorize** button and paste the token.",
    "",
    f"Total: {sum(len(v) for v in groups.values())} endpoints.",
    "",
]
for tag in sorted(groups):
    lines += [f"## {tag}", "", "| Method | Path | What it does | Login needed |", "| --- | --- | --- | --- |"]
    for method, path, summary, login in sorted(groups[tag], key=lambda r: (r[1], r[0])):
        lines.append(f"| {method} | `{path}` | {summary} | {'yes' if login else 'no'} |")
    lines.append("")

Path(__file__).with_name("API.md").write_text("\n".join(lines), encoding="utf-8")
print("Wrote docs/API.md")
