import json
import redis.asyncio as aioredis
from app.core.config import settings


def get_redis() -> aioredis.Redis:
    return aioredis.from_url(settings.redis_url, decode_responses=True)


async def publish_workflow_event(workflow_run_id: int, event: dict) -> None:
    r = get_redis()
    await r.publish(f"workflow:{workflow_run_id}", json.dumps(event))
