from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.research_session import ResearchSession
from app.models.workflow import WorkflowRun, WorkflowTask


router = APIRouter(prefix="/sessions", tags=["sessions"])

class CreateSessionRequest(BaseModel):
    title: str
    description: str | None = None

class UpdateSessionRequest(BaseModel):
    title: str

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_session(
    body: CreateSessionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    session = ResearchSession(
        user_id=current_user.id,
        title=body.title,
        description=body.description
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return {"id": session.id, "title": session.title, "description": session.description}

@router.get("")
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(ResearchSession).where(ResearchSession.user_id == current_user.id)
    )
    sessions = result.scalars().all()
    return [{"id": s.id, "title": s.title, "description": s.description} for s in sessions]


@router.get("/{session_id}")
async def get_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(ResearchSession).where(
            ResearchSession.id == session_id,
            ResearchSession.user_id == current_user.id
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"id": session.id, "title": session.title, "description": session.description}


@router.patch("/{session_id}")
async def update_session(
    session_id: int,
    body: UpdateSessionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ResearchSession).where(
            ResearchSession.id == session_id,
            ResearchSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.title = body.title
    await db.commit()
    return {"id": session.id, "title": session.title}


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(ResearchSession).where(
            ResearchSession.id == session_id,
            ResearchSession.user_id == current_user.id
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    await db.delete(session)
    await db.commit()


@router.get("/{session_id}/history")
async def get_session_history(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session_result = await db.execute(
        select(ResearchSession).where(
            ResearchSession.id == session_id,
            ResearchSession.user_id == current_user.id,
        )
    )
    if not session_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Session not found")

    runs_result = await db.execute(
        select(WorkflowRun)
        .where(WorkflowRun.session_id == session_id)
        .order_by(WorkflowRun.created_at)
    )
    runs = runs_result.scalars().all()

    messages = []
    for run in runs:
        messages.append({"role": "user", "content": run.question, "created_at": str(run.created_at)})
        if run.status == "completed":
            tasks_result = await db.execute(
                select(WorkflowTask)
                .where(
                    WorkflowTask.workflow_run_id == run.id,
                    WorkflowTask.task_type == "research",
                    WorkflowTask.status == "completed",
                )
            )
            task = tasks_result.scalar_one_or_none()
            if task and task.result:
                report = task.result.get("report", "")
                if report:
                    messages.append({"role": "assistant", "content": report, "created_at": str(task.updated_at)})
    return messages