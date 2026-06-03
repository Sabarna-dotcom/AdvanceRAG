"""
Cache routes — inspect and manage the Redis query/embedding cache.

Routes:
    GET    /cache/stats   — show how many items are cached
    DELETE /cache/flush   — clear all cache entries (keeps sessions intact)
    DELETE /cache/query   — invalidate cache for a specific query
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional

from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ==========================================
# Response Models
# ==========================================

class CacheStatsResponse(BaseModel):
    redis_reachable: bool        = Field(..., description="True if Redis responded.")
    query_cache_count: int       = Field(default=0, description="Number of cached query results.")
    embedding_cache_count: int   = Field(default=0, description="Number of cached embeddings.")
    semantic_index_count: int    = Field(default=0, description="Entries in semantic similarity index.")
    ttl_query_seconds: int       = Field(default=0, description="TTL for query results (seconds).")
    ttl_embedding_seconds: int   = Field(default=0, description="TTL for embeddings (seconds).")
    similarity_threshold: float  = Field(default=0.95, description="Cosine similarity threshold for semantic cache hits.")


class CacheFlushResponse(BaseModel):
    deleted_keys: int = Field(..., description="Number of cache keys deleted.")
    message: str      = Field(default="Cache flushed successfully.")


class CacheInvalidateRequest(BaseModel):
    query: str                     = Field(..., description="The query to remove from cache.")
    collection: Optional[str]      = Field(default=None, description="'pdf', 'audio', or None for both.")


class CacheInvalidateResponse(BaseModel):
    message: str = Field(...)


# ==========================================
# Routes
# ==========================================

@router.get(
    "/cache/stats",
    response_model=CacheStatsResponse,
    summary="Cache Statistics",
    description=(
        "Returns how many query results and embeddings are currently cached in Redis. "
        "Useful to verify caching is working."
    ),
)
async def cache_stats() -> CacheStatsResponse:
    """Return current Redis cache statistics."""
    from src.memory.cache_manager import CacheManager

    cache = CacheManager()
    stats = cache.get_stats()

    logger.info(f"GET /cache/stats | {stats}")

    return CacheStatsResponse(
        redis_reachable=stats.get("redis_reachable", False),
        query_cache_count=stats.get("query_cache_count", 0),
        embedding_cache_count=stats.get("embedding_cache_count", 0),
        semantic_index_count=stats.get("semantic_index_count", 0),
        ttl_query_seconds=stats.get("ttl_query_seconds", 0),
        ttl_embedding_seconds=stats.get("ttl_embedding_seconds", 0),
        similarity_threshold=stats.get("similarity_threshold", 0.95),
    )


@router.delete(
    "/cache/flush",
    response_model=CacheFlushResponse,
    summary="Flush All Cache",
    description=(
        "Deletes ALL cached query results and embeddings from Redis. "
        "Does NOT delete chat sessions (those are under 'session:' prefix). "
        "Use this after re-ingesting new documents so stale answers are removed."
    ),
)
async def flush_cache() -> CacheFlushResponse:
    """Flush all cache:* keys from Redis."""
    from src.memory.cache_manager import CacheManager

    cache = CacheManager()
    deleted = cache.flush_all_cache()

    logger.info(f"DELETE /cache/flush | deleted={deleted} keys")

    return CacheFlushResponse(
        deleted_keys=deleted,
        message=f"Cache flushed. {deleted} keys deleted.",
    )


@router.delete(
    "/cache/query",
    response_model=CacheInvalidateResponse,
    summary="Invalidate Specific Query Cache",
    description=(
        "Remove the cached result for one specific query. "
        "Useful when you know a particular question has a stale answer."
    ),
)
async def invalidate_query_cache(request: CacheInvalidateRequest) -> CacheInvalidateResponse:
    """Invalidate cache for a specific query + collection."""
    from src.memory.cache_manager import CacheManager

    cache = CacheManager()
    cache.invalidate_query(query=request.query, collection=request.collection)

    logger.info(
        f"DELETE /cache/query | query='{request.query[:60]}' | collection={request.collection}"
    )

    return CacheInvalidateResponse(
        message=f"Cache invalidated for query: '{request.query[:60]}'"
    )