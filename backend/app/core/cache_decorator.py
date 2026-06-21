import functools
from app.core.cache import cache_get, cache_set


def cached(key_fn, ttl: int = 3600):
    def decorator(fn):
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            key = key_fn(*args, **kwargs)
            hit = await cache_get(key)
            if hit is not None:
                return hit
            result = await fn(*args, **kwargs)
            if result is not None:
                await cache_set(key, result, ttl)
            return result
        return wrapper
    return decorator
