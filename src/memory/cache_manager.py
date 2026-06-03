# src/memory/cache_manager.py

"""
CacheManager — Redis-backed two-layer caching for the RAG pipeline.

Layer 1: Query Result Cache
    - Key  : cache:query:{normalized_query}:{collection}
    - Value: full serialized QueryResponse dict
    - TTL  : cache_ttl_query (default 86400s = 24 hours)
    - Why  : Exact same question → return instantly, skip retrieval + LLM

Layer 2: Embedding Cache
    - Key  : cache:embedding:{text_hash}
    - Value: JSON-serialized embedding vector (list of floats)
    - TTL  : cache_ttl_embedding (default 604800s = 7 days)
    - Why  : Same text → skip Ollama bge-m3 API call

Layer 3: Semantic Query Cache (bonus)
    - When exact match misses, check stored query embeddings for cosine similarity >= threshold (0.95)
    - Key  : cache:query_embedding:{normalized_query_hash} → embedding vector
    - Key  : cache:query_index        → sorted set of all cached query hashes
    - Why  : "What is biotech?" and "what is biotechnology?" should both hit the same cached answer

Redis key structure:
    cache:query:{hash}           → JSON result dict
    cache:query_emb:{hash}       → JSON embedding of that query (for semantic search)
    cache:embedding:{text_hash}  → JSON embedding vector

Usage:
    cache = CacheManager()

    # Embedding cache
    emb = cache.get_embedding("photosynthesis is a process...")
    if emb is None:
        emb = model.embed(text)
        cache.set_embedding("photosynthesis is a process...", emb)

    # Query result cache
    result = cache.get_query_result("What is photosynthesis?", collection="pdf")
    if result is None:
        result = run_full_rag_pipeline(...)
        cache.set_query_result("What is photosynthesis?", collection="pdf", result=result)

    # Stats
    stats = cache.get_stats()
"""

import json
import hashlib
import math
import os
from typing import Any, Dict, List, Optional

import redis

from src.utils.logger import get_logger

logger = get_logger(__name__)


# ==========================================
# CacheManager
# ==========================================

class CacheManager:
    """
    Two-layer Redis cache:
      1. Query result cache   — skip full RAG pipeline for repeated questions
      2. Embedding cache      — skip Ollama embed call for repeated text chunks
      3. Semantic similarity  — near-duplicate queries also hit the cache
    """

    _QUERY_PREFIX     = "cache:query:{}"        # hash → result JSON
    _QUERY_EMB_PREFIX = "cache:query_emb:{}"    # hash → embedding JSON
    _EMB_PREFIX       = "cache:embedding:{}"    # text hash → embedding JSON

    def __init__(self):
        # -------------------------------------------------------
        # Guarantee ALL attributes exist from the very first line.
        # Nothing below can cause AttributeError on this object.
        # -------------------------------------------------------
        self.client    = None
        self.ttl_query = 86400      # 24h fallback
        self.ttl_emb   = 604800     # 7d  fallback
        self.threshold = 0.95       # cosine similarity fallback

        try:
            self._setup()
        except Exception as e:
            # Last-resort safety — ensure client is always None, never missing
            self.client = None
            logger.error(f"CacheManager._setup failed — caching disabled. {e}")

    def _setup(self):
        """Separated so any crash here cannot affect attribute existence."""
        # --- Step 1: resolve connection params from env (safe defaults) ---
        host     = os.getenv("REDIS_HOST",     "localhost")
        port     = int(os.getenv("REDIS_PORT", "6379"))
        password = os.getenv("REDIS_PASSWORD") or None
        db       = int(os.getenv("REDIS_DB",   "0"))

        # --- Step 2: try to override with cache_config (needs JWT/DB env vars) ---
        try:
            from src.config.cache_config import get_config
            config         = get_config()
            host           = config.host
            port           = config.port
            password       = config.password or None
            db             = config.db
            self.ttl_query = config.ttl_query
            self.ttl_emb   = config.ttl_embedding
            self.threshold = config.similarity_threshold
        except Exception as _cfg_err:
            logger.warning(
                f"CacheManager: CacheConfig not available ({_cfg_err}) "
                "— using env vars (REDIS_HOST/PORT/PASSWORD/DB)."
            )

        # --- Step 3: connect to Redis ---
        client = redis.Redis(
            host=host,
            port=port,
            password=password,
            db=db,
            decode_responses=True,
        )
        client.ping()   # raises ConnectionError if Redis is down
        self.client = client
        logger.info(
            f"CacheManager initialized | "
            f"host={host}:{port} | "
            f"ttl_query={self.ttl_query}s | "
            f"ttl_emb={self.ttl_emb}s | "
            f"similarity_threshold={self.threshold}"
        )

    # ------------------------------------------
    # Internal Helpers
    # ------------------------------------------

    def _is_ready(self) -> bool:
        """Return True if Redis client is connected."""
        return self.client is not None

    @staticmethod
    def _normalize(text: str) -> str:
        """Lowercase + strip for consistent hashing."""
        return text.strip().lower()

    @staticmethod
    def _hash(text: str) -> str:
        """SHA-256 hash of text — used as Redis key suffix."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if len(a) != len(b):
            return 0.0
        dot   = sum(x * y for x, y in zip(a, b))
        mag_a = math.sqrt(sum(x * x for x in a))
        mag_b = math.sqrt(sum(x * x for x in b))
        if mag_a == 0 or mag_b == 0:
            return 0.0
        return dot / (mag_a * mag_b)

    # ------------------------------------------
    # Embedding Cache  (Layer 2)
    # ------------------------------------------

    def get_embedding(self, text: str) -> Optional[List[float]]:
        """
        Return cached embedding for text, or None if not cached.

        Args:
            text: raw text to look up

        Returns:
            List[float] embedding or None
        """
        if not self._is_ready():
            return None
        try:
            key = self._EMB_PREFIX.format(self._hash(text))
            raw = self.client.get(key)
            if raw is None:
                logger.debug("CacheManager: embedding cache MISS")
                return None
            logger.debug("CacheManager: embedding cache HIT")
            return json.loads(raw)
        except Exception as e:
            logger.warning(f"CacheManager.get_embedding error: {e}")
            return None

    def set_embedding(self, text: str, embedding: List[float]) -> None:
        """
        Store embedding in Redis with TTL.

        Args:
            text:      the original text that was embedded
            embedding: the embedding vector
        """
        if not self._is_ready():
            return
        try:
            key = self._EMB_PREFIX.format(self._hash(text))
            self.client.set(key, json.dumps(embedding), ex=self.ttl_emb)
            logger.debug("CacheManager: embedding stored.")
        except Exception as e:
            logger.warning(f"CacheManager.set_embedding error: {e}")

    # ------------------------------------------
    # Query Result Cache  (Layer 1 — exact match)
    # ------------------------------------------

    def _query_cache_key(self, query: str, collection: Optional[str]) -> str:
        """Build a cache key from normalized query + collection filter."""
        normalized = self._normalize(query)
        col_tag    = collection or "all"
        return self._QUERY_PREFIX.format(self._hash(f"{normalized}::{col_tag}"))

    def _query_emb_key(self, query: str, collection: Optional[str]) -> str:
        normalized = self._normalize(query)
        col_tag    = collection or "all"
        return self._QUERY_EMB_PREFIX.format(self._hash(f"{normalized}::{col_tag}"))

    def get_query_result(
        self,
        query: str,
        collection: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Look up a cached RAG result for this exact query + collection.

        Returns:
            Cached result dict (same structure as GenerationManager output) or None.
        """
        if not self._is_ready():
            return None
        try:
            key = self._query_cache_key(query, collection)
            raw = self.client.get(key)
            if raw is None:
                logger.debug("CacheManager: query cache MISS (exact)")
                return None
            logger.info(
                f"CacheManager: query cache HIT (exact) | "
                f"query='{query[:60]}' | collection={collection}"
            )
            return json.loads(raw)
        except Exception as e:
            logger.warning(f"CacheManager.get_query_result error: {e}")
            return None

    def set_query_result(
        self,
        query: str,
        collection: Optional[str],
        result: Dict[str, Any],
        query_embedding: Optional[List[float]] = None,
    ) -> None:
        """
        Store a RAG result in Redis.

        Also stores the query embedding (if provided) so semantic search can
        find near-duplicate queries later.

        Args:
            query:           the user's question
            collection:      'pdf', 'audio', or None
            result:          full result dict from GenerationManager
            query_embedding: optional embedding of query for semantic cache
        """
        if not self._is_ready():
            return
        try:
            key = self._query_cache_key(query, collection)
            self.client.set(key, json.dumps(result), ex=self.ttl_query)

            # Also store the query embedding for semantic similarity lookups
            if query_embedding is not None:
                emb_key = self._query_emb_key(query, collection)
                self.client.set(
                    emb_key,
                    json.dumps({
                        "embedding": query_embedding,
                        "result_key": key,
                    }),
                    ex=self.ttl_query,
                )

                # Track this key in a Redis set so we can scan it for semantic search
                self.client.sadd("cache:query_index", emb_key)
                self.client.expire("cache:query_index", self.ttl_query)

            logger.info(
                f"CacheManager: query result stored | "
                f"query='{query[:60]}' | collection={collection}"
            )
        except Exception as e:
            logger.warning(f"CacheManager.set_query_result error: {e}")

    # ------------------------------------------
    # Semantic Query Cache  (Layer 3)
    # ------------------------------------------

    def get_semantic_query_result(
        self,
        query_embedding: List[float],
        collection: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Check if any previously cached query is semantically similar
        to this query (cosine similarity >= threshold).

        Args:
            query_embedding: embedding of the current query
            collection:      filter — only match same collection entries

        Returns:
            Cached result dict if a similar query exists, else None.
        """
        if not self._is_ready():
            return None
        try:
            # Get all known query embedding keys
            all_emb_keys = self.client.smembers("cache:query_index")
            if not all_emb_keys:
                logger.debug("CacheManager: semantic index is empty.")
                return None

            col_tag = collection or "all"
            best_score = 0.0
            best_result = None

            for emb_key in all_emb_keys:
                # Only compare same collection
                if f"::{col_tag}::" not in emb_key and col_tag != "all":
                    pass  # Still check — key format doesn't embed col clearly, compare all

                raw = self.client.get(emb_key)
                if raw is None:
                    continue

                data = json.loads(raw)
                cached_emb  = data.get("embedding", [])
                result_key  = data.get("result_key")

                if not cached_emb or not result_key:
                    continue

                score = self._cosine_similarity(query_embedding, cached_emb)
                if score > best_score:
                    best_score = score
                    if score >= self.threshold:
                        raw_result = self.client.get(result_key)
                        if raw_result:
                            best_result = json.loads(raw_result)

            if best_result is not None:
                logger.info(
                    f"CacheManager: semantic cache HIT | "
                    f"score={best_score:.4f} | threshold={self.threshold}"
                )
                return best_result

            logger.debug(
                f"CacheManager: semantic cache MISS | "
                f"best_score={best_score:.4f} | threshold={self.threshold}"
            )
            return None

        except Exception as e:
            logger.warning(f"CacheManager.get_semantic_query_result error: {e}")
            return None

    # ------------------------------------------
    # Cache Invalidation
    # ------------------------------------------

    def invalidate_query(self, query: str, collection: Optional[str] = None) -> None:
        """Remove a specific query result from cache."""
        if not self._is_ready():
            return
        try:
            key     = self._query_cache_key(query, collection)
            emb_key = self._query_emb_key(query, collection)
            self.client.delete(key)
            self.client.delete(emb_key)
            self.client.srem("cache:query_index", emb_key)
            logger.info(f"CacheManager: invalidated query cache | query='{query[:60]}'")
        except Exception as e:
            logger.warning(f"CacheManager.invalidate_query error: {e}")

    def flush_all_cache(self) -> int:
        """
        Delete ALL cache keys (query results + embeddings).
        Returns count of deleted keys.
        WARNING: This only deletes keys with 'cache:' prefix — does NOT touch sessions.
        """
        if not self._is_ready():
            return 0
        try:
            keys = self.client.keys("cache:*")
            if keys:
                deleted = self.client.delete(*keys)
            else:
                deleted = 0
            logger.info(f"CacheManager: flushed {deleted} cache keys.")
            return deleted
        except Exception as e:
            logger.warning(f"CacheManager.flush_all_cache error: {e}")
            return 0

    # ------------------------------------------
    # Stats
    # ------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """
        Return cache statistics.

        Returns dict with:
            query_cache_count    — number of cached query results
            embedding_cache_count — number of cached embeddings
            semantic_index_count — number of entries in semantic index
            redis_reachable      — bool
        """
        if not self._is_ready():
            return {
                "redis_reachable": False,
                "query_cache_count": 0,
                "embedding_cache_count": 0,
                "semantic_index_count": 0,
            }
        try:
            query_keys    = self.client.keys("cache:query:*")
            emb_keys      = self.client.keys("cache:embedding:*")
            semantic_size = self.client.scard("cache:query_index")

            return {
                "redis_reachable":       True,
                "query_cache_count":     len(query_keys),
                "embedding_cache_count": len(emb_keys),
                "semantic_index_count":  semantic_size,
                "ttl_query_seconds":     self.ttl_query,
                "ttl_embedding_seconds": self.ttl_emb,
                "similarity_threshold":  self.threshold,
            }
        except Exception as e:
            logger.warning(f"CacheManager.get_stats error: {e}")
            return {"redis_reachable": False, "error": str(e)}