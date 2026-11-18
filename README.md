# AgentOS

AI-powered autonomous operations agent platform (Next.js + FastAPI + LangGraph + pgvector).

## Setup
```bash
cp .env.example .env
docker compose -f infra/docker-compose.yml up -d
cd backend && python -m venv venv && venv\Scripts\activate && pip install -r requirements.txt && cd ..
python -m contracts.seed
uvicorn backend.main:app --reload
```
API docs: http://localhost:8000/docs

## Rules
- Each person edits only their own folders (see Folder Structure PDF).
- Do not change `backend/db/models.py` without telling the other person.
- Work on a branch, merge by Pull Request.