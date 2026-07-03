# src/monitoring/metrics.py
"""
Custom Prometheus metrics for the RAG system.

All metrics are module-level singletons — safe to import anywhere.

Usage:
    from src.monitoring.metrics import QUERY_TOTAL, QUERY_DURATION
    QUERY_TOTAL.labels(collection="pdf", has_answer="true", cached="false").inc()
"""

from prometheus_client import Counter, Histogram, Gauge

# ==========================================
# Query Metrics
# ==========================================

QUERY_TOTAL = Counter(
    "rag_queries_total",
    "Total number of RAG queries processed.",
    ["collection", "has_answer", "cached"],
)

QUERY_DURATION = Histogram(
    "rag_query_duration_seconds",
    "End-to-end query duration in seconds.",
    ["collection"],
    buckets=[0.5, 1.0, 2.0, 3.0, 5.0, 10.0, 20.0, 30.0, 60.0],
)

QUERY_ITERATIONS = Histogram(
    "rag_query_self_reflection_iterations",
    "Number of self-reflection iterations per query.",
    buckets=[1, 2, 3, 4, 5],
)

QUERY_CITED_SOURCES = Histogram(
    "rag_query_cited_sources",
    "Number of cited sources returned per query.",
    buckets=[0, 1, 2, 3, 5, 7, 10],
)

# ==========================================
# Cache Metrics
# ==========================================

CACHE_HITS = Counter(
    "rag_cache_hits_total",
    "Number of cache hits (query result served from Redis cache).",
    ["collection"],
)

CACHE_MISSES = Counter(
    "rag_cache_misses_total",
    "Number of cache misses (full RAG pipeline executed).",
    ["collection"],
)

# ==========================================
# Retrieval Metrics
# ==========================================

RETRIEVAL_CHUNKS = Histogram(
    "rag_retrieval_chunks_retrieved",
    "Number of chunks retrieved per query.",
    buckets=[0, 1, 3, 5, 10, 15, 20, 30],
)

RETRIEVAL_STRATEGY = Counter(
    "rag_retrieval_strategy_total",
    "Retrieval strategies used.",
    ["strategy"],
)

# ==========================================
# Auth Metrics
# ==========================================

AUTH_LOGIN_TOTAL = Counter(
    "rag_auth_login_attempts_total",
    "Total login attempts.",
    ["success"],   # "true" or "false"
)

AUTH_REGISTER_TOTAL = Counter(
    "rag_auth_registrations_total",
    "Total user registrations.",
)

AUTH_TOKEN_REFRESH_TOTAL = Counter(
    "rag_auth_token_refresh_total",
    "Total token refresh operations.",
)

# ==========================================
# Session Metrics
# ==========================================

SESSION_CREATED_TOTAL = Counter(
    "rag_sessions_created_total",
    "Total sessions created.",
)

SESSION_ACTIVE = Gauge(
    "rag_sessions_active",
    "Number of currently active sessions in Redis.",
)

# ==========================================
# LLM Metrics
# ==========================================

LLM_CALLS_TOTAL = Counter(
    "rag_llm_calls_total",
    "Total LLM API calls made.",
    ["model"],
)

LLM_DURATION = Histogram(
    "rag_llm_call_duration_seconds",
    "LLM call duration in seconds.",
    ["model"],
    buckets=[1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0],
)

# ==========================================
# Ingestion Metrics
# ==========================================

INGESTION_FILES_TOTAL = Counter(
    "rag_ingestion_files_total",
    "Total files ingested.",
    ["file_type"],   # "pdf" or "audio"
)

INGESTION_CHUNKS_TOTAL = Counter(
    "rag_ingestion_chunks_total",
    "Total chunks created during ingestion.",
    ["file_type"],
)

# ==========================================
# Error Metrics
# ==========================================

ERRORS_TOTAL = Counter(
    "rag_errors_total",
    "Total errors by component.",
    ["component"],   # "retrieval", "generation", "auth", "cache"
)
