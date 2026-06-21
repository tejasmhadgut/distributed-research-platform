from fastapi import FastAPI
from app.api.routes import auth, sessions, workflows, ws
from app.api.routes import financial
from app.api.routes.documents import router as documents_router
import app.tools.financial_tools  # noqa: F401
import app.tools.document_tools   # noqa: F401
from app.api.routes.tools import router as tools_router
from app.api.routes.research import router as research_router


app = FastAPI(title="Distributed Research Platform")

app.include_router(auth.router, prefix="/api/v1")
app.include_router(sessions.router, prefix="/api/v1")
app.include_router(workflows.router, prefix="/api/v1")
app.include_router(financial.router, prefix="/api/v1")
app.include_router(ws.router)
app.include_router(documents_router)
app.include_router(tools_router)
app.include_router(research_router)

@app.get("/health")
async def health():
    return {"status": "ok"}
