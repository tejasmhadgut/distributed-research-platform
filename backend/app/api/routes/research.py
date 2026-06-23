from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.research_session import ResearchSession
from app.services.workflow_service import create_workflow

router = APIRouter(prefix="/research", tags=["research"])


class ResearchRequest(BaseModel):
    session_id: int
    question: str
    ticker: str


@router.post("")
async def start_research(
    body: ResearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ResearchSession).where(
            ResearchSession.id == body.session_id,
            ResearchSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    run = await create_workflow(
        db,
        body.session_id,
        body.question,
        "research",
        {"question": body.question, "ticker": body.ticker},
    )
    return {"workflow_run_id": run.id, "status": run.status}

from app.services.workflow_service import get_workflow, get_workflow_tasks


@router.get("/{workflow_run_id}")
async def get_research_result(
    workflow_run_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    run = await get_workflow(db, workflow_run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Not found")
    tasks = await get_workflow_tasks(db, workflow_run_id)
    research_task = next((t for t in tasks if t.task_type == "research"), None)
    return {
        "workflow_run_id": run.id,
        "status": run.status,
        "result": research_task.result if research_task else None,
    }
