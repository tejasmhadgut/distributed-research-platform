import json
import redis.asyncio as aioredis
from app.core.config import settings

_client: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _client
    if _client is None:
        _client = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _client


async def cache_get(key: str) -> dict | list | None:
    client = get_redis()
    value = await client.get(key)
    if value is None:
        return None
    return json.loads(value)


async def cache_set(key: str, value: dict | list, ttl: int):
    client = get_redis()
    await client.setex(key, ttl, json.dumps(value, default=str))


async def cache_delete(key: str):
    client = get_redis()
    await client.delete(key)
