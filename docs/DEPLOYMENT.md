# Running and deploying AgentOS

## 1. Development (what you use every day)

```bash
docker compose -f infra/docker-compose.yml up -d      # Postgres + Redis only
python -m contracts.seed                               # tables + demo data (safe to repeat)
uvicorn backend.main:app --reload                      # backend on :8000
cd frontend && npm run dev                             # frontend on :3000
ollama serve                                           # local LLM
```

Start Docker Desktop first on Windows. Demo login: `demo@agentos.dev` / `demo123`.

## 2. The whole app in containers

```bash
cp .env.example .env            # set JWT_SECRET to a long random value
docker compose --env-file .env -f infra/docker-compose.yml --profile full up --build -d
```

| Service | Address | Image |
| --- | --- | --- |
| frontend | http://localhost:3000 | `infra/frontend.Dockerfile` (Node 22, Next.js build) |
| backend | http://localhost:8000 (docs at `/docs`) | `infra/backend.Dockerfile` (Python 3.12, CPU PyTorch, model pre-downloaded) |
| db | localhost:5432 | `pgvector/pgvector:pg16` |
| redis | localhost:6379 | `redis:7` |

- `--env-file .env` is needed because Docker Compose otherwise looks for `.env` next to the compose file (in `infra/`).
- The backend container creates the tables and demo data when it starts, then starts the API.
- Ollama runs on your own computer; the backend reaches it at `host.docker.internal:11434`.
- Uploaded CSV files live in the `storage` volume and the database in the `pgdata` volume. `docker compose ... down` keeps them; `down -v` deletes them.
- The frontend has the backend address (`NEXT_PUBLIC_API_URL`) built in. To serve it from another address, rebuild with `--build-arg`.
- The first backend build is slow (PyTorch and the embedding model are downloaded). Later builds reuse the cache.

Useful commands:

```bash
docker compose -f infra/docker-compose.yml --profile full ps
docker compose -f infra/docker-compose.yml --profile full logs -f backend
docker compose -f infra/docker-compose.yml --profile full down
```

## 3. Continuous integration (GitHub Actions)

`.github/workflows/ci.yml` runs on every push to `main` and on every pull request:

| Job | Steps |
| --- | --- |
| Backend tests | install dependencies, `pytest backend/tests` |
| Frontend | `npm ci`, `npm run lint`, `tsc --noEmit`, `npm run build` |

Turn on "Require status checks" for `main` in the repository settings, so a pull request cannot be merged while a check fails.

## 4. Settings

See the table in the README. Before showing the project to others, change `JWT_SECRET`, change the database password in `infra/docker-compose.yml`, and remove or change the demo user.

## 5. Regenerating the API reference

```bash
python docs/generate_api_docs.py
```
