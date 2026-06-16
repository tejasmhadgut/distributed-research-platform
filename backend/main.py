from fastapi import FastAPI
from app.core.config import settings
from app.api.routes import auth, sessions, workflows

app = FastAPI(title="Distributed Research Platform")

app.include_router(auth.router, prefix="/api/v1")
app.include_router(sessions.router, prefix="/api/v1")
app.include_router(workflows.router, prefix="/api/v1")

@app.get("/health")
async def health():
    return {"status":"ok"}


