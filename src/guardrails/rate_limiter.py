# src/guardrails/rate_limiter.py
"""
RateLimiter — Redis-backed per-IP / per-session request rate limiting.

Limits:
  - per_user_hour  : max requests per IP in a rolling 1-hour window
  - per_user_day   : max requests per IP in a rolling 24-hour window

Uses Redis INCR + EXPIRE — atomic, no race conditions.

Usage (in FastAPI route or middleware):
    limiter = RateLimiter()
    result  = limiter.check(identifier="127.0.0.1")
    if not result.allowed:
        raise HTTPException(429, result.reason)
"""

from dataclasses import dataclass
from typing import Optional

import redis

from src.config.guardrails_config import get_config
from src.memory.memory_config import get_config as get_memory_config
from src.utils.logger import get_logger

logger = get_logger(__name__)


# ==========================================
# Result dataclass
# ==========================================

@dataclass
class RateLimitResult:
    allowed: bool
    reason: Optional[str] = None
    requests_this_hour: int = 0
    requests_today: int = 0
    limit_hour: int = 0
    limit_day: int = 0


# ==========================================
# RateLimiter
# ==========================================

class RateLimiter:
    """
    Redis-backed sliding window rate limiter.

    Keys:
        ratelimit:{identifier}:hour   — expires in 3600s
        ratelimit:{identifier}:day    — expires in 86400s
    """

    _HOUR_TTL = 3600
    _DAY_TTL  = 86400

    def __init__(self):
        self.config     = get_config().rate_limit
        mem_config      = get_memory_config()

        self.client = redis.Redis(
            host=mem_config.host,
            port=mem_config.port,
            password=mem_config.password or None,
            db=mem_config.db,
            decode_responses=True,
        )
        self.client.ping()
        logger.info(
            f"RateLimiter initialized | "
            f"hour_limit={self.config.per_user_hour} | "
            f"day_limit={self.config.per_user_day}"
        )

    # ------------------------------------------
    # Public entry point
    # ------------------------------------------

    def check(self, identifier: str) -> RateLimitResult:
        """
        Increment counters and check against limits.

        Args:
            identifier : typically the client IP address,
                         or session_id if you have one.
        """
        hour_key = f"ratelimit:{identifier}:hour"
        day_key  = f"ratelimit:{identifier}:day"

        try:
            pipe = self.client.pipeline()

            # Increment both counters atomically
            pipe.incr(hour_key)
            pipe.incr(day_key)
            pipe.ttl(hour_key)
            pipe.ttl(day_key)

            hour_count, day_count, hour_ttl, day_ttl = pipe.execute()

            # Set TTL only on first request (ttl == -1 means no expiry set yet)
            if hour_ttl == -1:
                self.client.expire(hour_key, self._HOUR_TTL)
            if day_ttl == -1:
                self.client.expire(day_key, self._DAY_TTL)

            hour_count = int(hour_count)
            day_count  = int(day_count)

            # Check hour limit
            if hour_count > self.config.per_user_hour:
                logger.warning(
                    f"RateLimiter: hour limit exceeded | "
                    f"identifier={identifier} count={hour_count} limit={self.config.per_user_hour}"
                )
                return RateLimitResult(
                    allowed=False,
                    reason=f"Hourly limit of {self.config.per_user_hour} requests exceeded. Try again later.",
                    requests_this_hour=hour_count,
                    requests_today=day_count,
                    limit_hour=self.config.per_user_hour,
                    limit_day=self.config.per_user_day,
                )

            # Check day limit
            if day_count > self.config.per_user_day:
                logger.warning(
                    f"RateLimiter: day limit exceeded | "
                    f"identifier={identifier} count={day_count} limit={self.config.per_user_day}"
                )
                return RateLimitResult(
                    allowed=False,
                    reason=f"Daily limit of {self.config.per_user_day} requests exceeded. Try again tomorrow.",
                    requests_this_hour=hour_count,
                    requests_today=day_count,
                    limit_hour=self.config.per_user_hour,
                    limit_day=self.config.per_user_day,
                )

            logger.debug(
                f"RateLimiter: OK | identifier={identifier} "
                f"hour={hour_count}/{self.config.per_user_hour} "
                f"day={day_count}/{self.config.per_user_day}"
            )

            return RateLimitResult(
                allowed=True,
                requests_this_hour=hour_count,
                requests_today=day_count,
                limit_hour=self.config.per_user_hour,
                limit_day=self.config.per_user_day,
            )

        except redis.exceptions.RedisError as e:
            # If Redis is down, fail open (allow request) — don't block the whole API
            logger.error(f"RateLimiter: Redis error — failing open. {e}")
            return RateLimitResult(allowed=True, reason="Rate limit check skipped (Redis unavailable).")
 