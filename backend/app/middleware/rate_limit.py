import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from jose import jwt, JWTError
from app.core.config import settings
from app.core.cache import get_redis

SKIP_PATHS = {"/health", "/api/v1/auth/login", "/api/v1/auth/register"}

LIMITS = {
    "/research": (10, 60),
    "/quant": (20, 60),
    "/tools": (30, 60),
}
DEFAULT_LIMIT = (60, 60)


def _get_limit(path: str) -> tuple[int, int]:
    for prefix, limit in LIMITS.items():
        if path.startswith(prefix):
            return limit
    return DEFAULT_LIMIT


def _extract_user_id(request: Request) -> str | None:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth[7:]
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        return str(payload.get("sub"))
    except JWTError:
        return None


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in SKIP_PATHS:
            return await call_next(request)

        user_id = _extract_user_id(request)
        if user_id is None:
            return await call_next(request)

        max_requests, window_seconds = _get_limit(request.url.path)
        window = int(time.time() / window_seconds)
        key = f"rl:{user_id}:{request.url.path.split('/')[1]}:{window}"

        redis = get_redis()
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, window_seconds)

        if count > max_requests:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": f"Rate limit exceeded. Max {max_requests} requests per {window_seconds}s."
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(max_requests)
        response.headers["X-RateLimit-Remaining"] = str(max(0, max_requests - count))
        return response
