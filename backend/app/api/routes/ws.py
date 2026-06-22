import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy import select
from jose import jwt, JWTError
from app.core.config import settings
from app.core.redis_client import get_redis
from app.core.database import AsyncSessionLocal
from app.models.research_session import ResearchSession
from app.models.workflow import WorkflowRun, WorkflowTask
from app.services.workflow_service import create_workflow

router = APIRouter()


@router.websocket("/ws/workflows/{workflow_run_id}")
async def workflow_progress(websocket: WebSocket, workflow_run_id: int):
    await websocket.accept()
    r = get_redis()
    pubsub = r.pubsub()
    await pubsub.subscribe(f"workflow:{workflow_run_id}")
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                await websocket.send_text(message["data"])
    except WebSocketDisconnect:
        pass
    finally:
        await pubsub.unsubscribe(f"workflow:{workflow_run_id}")
        await pubsub.aclose()


@router.websocket("/ws/session/{session_id}")
async def session_ws(
    websocket: WebSocket,
    session_id: int,
    token: str = Query(default=None),
):
    if not token:
        await websocket.close(code=1008)
        return
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
    except JWTError:
        await websocket.close(code=1008)
        return

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ResearchSession).where(
                ResearchSession.id == session_id,
                ResearchSession.user_id == user_id,
            )
        )
        if not result.scalar_one_or_none():
            await websocket.close(code=1008)
            return

        await websocket.accept()
        r = get_redis()

        try:
            while True:
                data = await websocket.receive_json()
                question = data.get("question", "")
                ticker = data.get("ticker", "")

                prior_runs_result = await db.execute(
                    select(WorkflowRun)
                    .where(WorkflowRun.session_id == session_id, WorkflowRun.status == "completed")
                    .order_by(WorkflowRun.created_at)
                )
                prior_runs = prior_runs_result.scalars().all()
                context = []
                for pr in prior_runs:
                    task_result = await db.execute(
                        select(WorkflowTask).where(
                            WorkflowTask.workflow_run_id == pr.id,
                            WorkflowTask.task_type == "research",
                            WorkflowTask.status == "completed",
                        )
                    )
                    pt = task_result.scalar_one_or_none()
                    if pt and pt.result and pt.result.get("report"):
                        context.append({"question": pr.question, "report": pt.result["report"]})

                run = await create_workflow(
                    db, session_id, question, "research",
                    {"question": question, "ticker": ticker, "context": context},
                )
                await websocket.send_json({"type": "workflow_started", "workflow_run_id": run.id})

                pubsub = r.pubsub()
                await pubsub.subscribe(f"workflow:{run.id}")
                async for message in pubsub.listen():
                    if message["type"] == "message":
                        await websocket.send_text(message["data"])
                        try:
                            if json.loads(message["data"]).get("status") in ("completed", "failed"):
                                break
                        except Exception:
                            pass
                await pubsub.unsubscribe(f"workflow:{run.id}")
                await pubsub.aclose()

        except WebSocketDisconnect:
            pass
