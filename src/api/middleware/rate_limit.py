# src/api/middleware/rate_limit.py

"""
Rate limit middleware - runs on every incoming request to /query and /ingest.
Returns HTTP 429 if the client IP has exceeded the configured limits.
"""

from fastapi import Request
from fastapi.responses import JSONResponse
from src.utils.logger import get_logger

logger = get_logger(__name__)

_RATE_LIMITED_PATHS = {"/query", "/ingest"}


async def rate_limit_middleware(request: Request, call_next):
    """Enforce per-IP rate limits on sensitive routes. Fails open if Redis is down."""

    if not any(request.url.path.startswith(p) for p in _RATE_LIMITED_PATHS):
        return await call_next(request)

    identifier = (
        request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or request.client.host
        or "unknown"
    )

    try:
        from src.guardrails.rate_limiter import RateLimiter

        limiter = RateLimiter()
        result = limiter.check(identifier)

        if not result.allowed:
            logger.warning(
                f"Rate limit exceeded | ip={identifier} path={request.url.path}"
            )

            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "message": result.reason,
                    "requests_this_hour": result.requests_this_hour,
                    "requests_today": result.requests_today,
                    "limit_hour": result.limit_hour,
                    "limit_day": result.limit_day,
                },
            )

    except Exception as e:
        logger.error(f"Rate limit middleware error - failing open: {e}")

    return await call_next(request)