from fastapi import FastAPI
from app.api.routes import auth, sessions, workflows, ws
from app.api.routes import financial
from app.api.routes.documents import router as documents_router

app = FastAPI(title="Distributed Research Platform")

app.include_router(auth.router, prefix="/api/v1")
app.include_router(sessions.router, prefix="/api/v1")
app.include_router(workflows.router, prefix="/api/v1")
app.include_router(financial.router, prefix="/api/v1")
app.include_router(ws.router)
app.include_router(documents_router)

@app.get("/health")
async def health():
    return {"status": "ok"}
