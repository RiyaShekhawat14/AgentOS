from fastapi import FastAPI

app = FastAPI(title="AgentOS")

@app.get("/health")
def health():
    return {"status": "ok"}