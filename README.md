# AgentOS

AI-powered autonomous operations agent platform. You create an agent, choose which tools it may use, give it a task, and watch it plan, work and answer. Risky actions wait for your approval.

Built by Riya Shekhawat and Khushi Akhar (B.E. AI & Data Science, MBM University) as a minor project.

**Stack:** Next.js + TypeScript + Tailwind (frontend), FastAPI + SQLAlchemy (backend), LangGraph (agent loop), Ollama (local LLM), Postgres + pgvector, Redis.

## How a run works

1. You write a task for an agent.
2. The agent loads its instructions, memory and the most relevant parts of your documents.
3. It writes a short plan, then repeats: choose a tool, check the permission, run it, read the result.
4. A tool is `auto` (runs now), `ask` (waits for you to Approve or Reject) or `blocked` (never runs). The `code` tool asks by default.
5. It gives a final answer and saves a short memory of the run.

Limits: 8 tool calls per run, 300 seconds per run (time spent waiting for you is not counted). You can stop a run at any time.

## Tools

| Tool | What it does |
| --- | --- |
| `web_search` | Searches the internet (DuckDuckGo) and returns title, link and snippet |
| `calculator` | Safe maths: arithmetic, percentages, mean, min, max... |
| `csv_reader` | Reads a CSV uploaded to the agent: columns, sample rows, totals by group, outliers |
| `code` | Runs a short Python script (10 second and 256 MB limit). Asks first by default |

## What is ready

| Part | Status |
| --- | --- |
| Agent builder (create, edit, delete agents; choose tools and permissions) | Done (API + UI) |
| Tools and CSV upload API | Done (API) |
| Permissions and approve / reject | Done (API) |
| Run engine, runs API, live stream | Done (API) |
| Run page (live step graph, approve buttons, result) | Done (UI) |
| Login and app shell | Done (API + UI) |
| Knowledge base (RAG): upload, list, delete, test search | Done (API + UI) |
| Memory: short and long term, viewer page | Done (API + UI) |
| Dashboard: cards and charts | Done (API + UI) |
| Scheduler: recurring runs | Done (API + UI) |
| Docker for the whole app, CI, docs | Done, see `docs/` |

Until the run page is built, start and watch runs from the API docs at http://localhost:8000/docs (log in with `POST /auth/login`, copy the token, press **Authorize**).

## Setup

You need Python 3.10+, Node 20+, Docker, and [Ollama](https://ollama.com).

```bash
# 1. settings
cp .env.example .env            # on Windows PowerShell: copy .env.example .env

# 2. database and redis
docker compose -f infra/docker-compose.yml up -d

# 3. backend (run from the project root)
cd backend && python -m venv venv && venv\Scripts\activate && pip install -r requirements.txt && cd ..
python -m contracts.seed        # creates the tables and demo data (safe to repeat)
uvicorn backend.main:app --reload

# 4. frontend (a second terminal)
cd frontend && npm install && npm run dev

# 5. local LLM (a third terminal, if Ollama is not already running)
ollama pull qwen2.5
ollama serve
```

- App: http://localhost:3000 (click **Register** on the login page to create your account, or log in as the demo user `demo@agentos.dev` / `demo123`)
- API docs: http://localhost:8000/docs
- Check that the model is ready: `GET /llm/status` in the API docs.

Use a model that follows instructions well (for example `qwen2.5` or `llama3.1`). Very small models may break the JSON format the agent needs.

## Settings (`.env`)

| Name | Meaning | Default |
| --- | --- | --- |
| `DATABASE_URL` | Postgres connection | the Docker database |
| `REDIS_URL` | Redis connection | local Redis |
| `JWT_SECRET` | Secret for login tokens. Change it | dev value |
| `OLLAMA_BASE_URL` | Where Ollama runs | `http://localhost:11434` |
| `OLLAMA_MODEL` | Model the agents use | `qwen2.5` |
| `AGENT_MAX_STEPS` | Tool calls allowed per run | `8` |
| `AGENT_RUN_TIMEOUT` | Seconds allowed per run | `300` |
| `STORAGE_DIR` | Folder for uploaded CSV files | `backend/storage` |
| `NEXT_PUBLIC_API_URL` | Backend address used by the frontend | `http://localhost:8000` |

## API at a glance

All endpoints except register and login need a login token. Each user only sees their own agents and runs.

| Endpoint | Purpose |
| --- | --- |
| `POST /auth/register`, `POST /auth/login` | Create an account, get a token |
| `GET/POST /agents`, `GET/PUT/DELETE /agents/{id}` | Agent builder |
| `GET/POST /agents/{id}/files`, `DELETE /agents/{id}/files/{name}` | CSV files for the agent |
| `POST /agents/{id}/runs` | Start a run with `{ "task": "..." }` |
| `GET /runs`, `GET /runs/{id}` | List runs, see steps and result |
| `GET /runs/{id}/stream` | Live updates (Server-Sent Events) |
| `GET /runs/{id}/approvals` | Steps waiting for your approval |
| `POST /runs/{id}/steps/{step_id}/approve` or `/reject` | Answer an approval |
| `POST /runs/{id}/stop` | Stop a run |
| `GET /llm/status` | Is Ollama ready? |
| `GET/POST /agents/{id}/knowledge`, `DELETE /agents/{id}/knowledge/{doc_id}`, `GET /agents/{id}/knowledge/search` | Documents the agent can read (RAG) |
| `GET/POST /agents/{id}/memory`, `DELETE /memory/{id}` | Agent memory |
| `GET /metrics` | Numbers for the dashboard |
| `GET/POST /schedules`, `PATCH/DELETE /schedules/{id}`, `POST /schedules/{id}/run-now` | Recurring runs |

## Run everything in Docker

```bash
docker compose --env-file .env -f infra/docker-compose.yml --profile full up --build -d
```

Starts Postgres, Redis, the backend (http://localhost:8000) and the frontend (http://localhost:3000). Ollama still runs on your own computer. More in `docs/DEPLOYMENT.md`.

## Tests

```bash
pip install -r backend/requirements-dev.txt
python -m pytest backend/tests
```

The tests use an in-memory database and a fake model, so they need no Docker and no Ollama. GitHub Actions runs them, plus the frontend lint and build, on every push and pull request.

More documents: `docs/ARCHITECTURE.md` (how it fits together), `docs/API.md` (every endpoint), `docs/DEPLOYMENT.md` (Docker and CI).

## Folders

```
backend/   agents, tools, approval, engine (LangGraph), runs, auth, rag, memory, metrics, scheduler, tests
frontend/  Next.js app (agents, runs, dashboard, knowledge, memory, schedule)
contracts/ seed data shared by both of us
infra/     docker-compose (Postgres + pgvector, Redis, optional backend and frontend) and Dockerfiles
docs/      project documents
```

## Rules

- Each person edits only their own folders (see the Folder Structure PDF).
- Do not change `backend/db/models.py` without telling the other person.
- Work on a branch, merge by Pull Request.
