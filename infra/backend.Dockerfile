# Backend image. Build from the project root:  docker build -f infra/backend.Dockerfile .
FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

# CPU-only PyTorch first: the default download includes huge GPU libraries we do not need.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Download the embedding model now so the first document upload is not slow.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

COPY backend backend
COPY contracts contracts

ENV STORAGE_DIR=/app/storage
EXPOSE 8000

# 1) create the tables and demo data (safe to repeat)  2) start the API
CMD ["sh", "-c", "python -m contracts.seed && uvicorn backend.main:app --host 0.0.0.0 --port 8000"]
