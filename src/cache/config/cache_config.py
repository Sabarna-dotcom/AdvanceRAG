# config/cache_config.py
"""
Configuration specific to the caching module (Redis).
"""

from pydantic import BaseModel
from src.config.settings import get_settings


class CacheConfig(BaseModel):
    """Configuration for Redis caching"""

    # Connection
    host: str
    port: int
    password: str
    db: int
    url: str

    # TTL settings (in seconds)
    ttl_query: int
    ttl_embedding: int

    # Similarity threshold for semantic cache
    similarity_threshold: float

    class Config:
        frozen = True


def get_cache_config() -> CacheConfig:
    """Create cache config from main settings"""
    settings = get_settings()

    return CacheConfig(
        host=settings.redis_host,
        port=settings.redis_port,
        password=settings.redis_password,
        db=settings.redis_db,
        url=settings.redis_url,
        ttl_query=settings.cache_ttl_query,
        ttl_embedding=settings.cache_ttl_embedding,
        similarity_threshold=settings.cache_similarity_threshold
    )


# Singleton
_cache_config = None


def get_config() -> CacheConfig:
    """Get or create cache config singleton"""
    global _cache_config
    if _cache_config is None:
        _cache_config = get_cache_config()
    return _cache_config