# src/memory/memory_config.py

"""
Configuration specific to the memory module.
Reads Redis settings directly from environment variables with safe defaults,
so it does NOT depend on the full Settings() which requires JWT_SECRET_KEY etc.
"""

import os
from pydantic import BaseModel


class MemoryConfig(BaseModel):
    """Configuration for Redis-backed session memory."""

    # Redis connection
    host: str
    port: int
    password: str
    db: int
    url: str

    # TTL for session history (seconds)
    ttl_session: int

    # Max number of chat turns to keep per session
    max_chat_history: int

    class Config:
        frozen = True


def get_memory_config() -> MemoryConfig:
    """
    Build memory config from environment variables directly.
    Falls back to safe defaults so Redis works even if
    JWT_SECRET_KEY / DATABASE_URL are not set yet.
    """

    host = os.getenv("REDIS_HOST", "localhost")
    port = int(os.getenv("REDIS_PORT", "6379"))
    password = os.getenv("REDIS_PASSWORD", "")
    db = int(os.getenv("REDIS_DB", "0"))

    # session_timeout_minutes → seconds
    ttl_session = int(os.getenv("SESSION_TIMEOUT_MINUTES", "60")) * 60

    max_chat_history = int(os.getenv("MAX_CHAT_HISTORY", "10"))

    # Build Redis URL
    if password:
        url = f"redis://:{password}@{host}:{port}/{db}"
    else:
        url = f"redis://{host}:{port}/{db}"

    return MemoryConfig(
        host=host,
        port=port,
        password=password,
        db=db,
        url=url,
        ttl_session=ttl_session,
        max_chat_history=max_chat_history,
    )


# Singleton
_memory_config = None


def get_config() -> MemoryConfig:
    """Get or create memory config singleton."""
    global _memory_config

    if _memory_config is None:
        _memory_config = get_memory_config()

    return _memory_config