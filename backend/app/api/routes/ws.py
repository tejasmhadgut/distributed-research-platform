import asyncio
import json
import redis.asyncio as aioredis
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.redis_client import get_redis

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
