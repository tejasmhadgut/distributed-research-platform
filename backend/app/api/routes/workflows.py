from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.research_session import ResearchSession
from app.services.workflow_service import create_workflow, get_workflow, get_workflow_tasks
from sqlalchemy import select

router = APIRouter(prefix="/workflows", tags=["workflows"])

class CreateWorkflowRequest(BaseModel):
    session_id: int
    question: str
    workflow_type: str = "compare_companies"
    input_data: dict = {}

@router.post("")
async def start_workflow(
    body: CreateWorkflowRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(ResearchSession).where(
            ResearchSession.id == body.session_id,
            ResearchSession.user_id == current_user.id
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    run = await create_workflow(db, body.session_id, body.question, body.workflow_type, body.input_data)
    return {"workflow_run_id": run.id, "status": run.status}

@router.get("/{workflow_run_id}")
async def get_workflow_status(
    workflow_run_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    run = await get_workflow(db, workflow_run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Workflow not found")
    tasks = await get_workflow_tasks(db, workflow_run_id)
    return {
        "id": run.id,
        "status": run.status,
        "question": run.question,
        "tasks": [{"id": t.id, "type": t.task_type, "status": t.status} for t in tasks]
    }