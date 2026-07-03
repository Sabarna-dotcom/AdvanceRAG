"""
Health check route.
GET /health — checks Qdrant, Ollama, Redis, and PostgreSQL.
"""

from fastapi import APIRouter
from src.api.models.response import HealthResponse
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Check if Qdrant, Ollama, Redis, and PostgreSQL are reachable.",
)
async def health_check() -> HealthResponse:
    """
    Ping all services and return per-service status.
    Overall status: 'ok' only if ALL services are healthy, else 'degraded'.
    """

    qdrant_ok   = False
    ollama_ok   = False
    redis_ok    = False
    postgres_ok = False
    details     = {}

    # --- Check Qdrant ---
    try:
        from qdrant_client import QdrantClient
        from src.config.vectorstore_config import get_config as get_vs_config
        vs_config = get_vs_config()
        client = QdrantClient(host=vs_config.host, port=vs_config.port, timeout=3)
        client.get_collections()
        qdrant_ok = True
        logger.info("Health: Qdrant OK")
    except Exception as e:
        details["qdrant_error"] = str(e)
        logger.warning(f"Health: Qdrant FAIL — {e}")

    # --- Check Ollama ---
    try:
        import requests as req
        from src.config.llm_config import get_config as get_llm_config
        llm_config = get_llm_config()
        resp = req.get(f"{llm_config.ollama_base_url}", timeout=3)
        ollama_ok = resp.status_code == 200
        logger.info("Health: Ollama OK")
    except Exception as e:
        details["ollama_error"] = str(e)
        logger.warning(f"Health: Ollama FAIL — {e}")

    # --- Check Redis ---
    try:
        from src.memory.memory_config import get_config as get_memory_config
        import redis
        mem_cfg = get_memory_config()
        r = redis.Redis(
            host=mem_cfg.host,
            port=mem_cfg.port,
            password=mem_cfg.password or None,
            db=mem_cfg.db,
            socket_connect_timeout=2,
        )
        r.ping()
        redis_ok = True
        logger.info("Health: Redis OK")
    except Exception as e:
        details["redis_error"] = str(e)
        logger.warning(f"Health: Redis FAIL — {e}")

    # --- Check PostgreSQL ---
    try:
        from src.database.connection import check_connection
        postgres_ok = check_connection()
        if postgres_ok:
            logger.info("Health: PostgreSQL OK")
        else:
            details["postgres_error"] = "Connection check returned False"
            logger.warning("Health: PostgreSQL FAIL")
    except Exception as e:
        details["postgres_error"] = str(e)
        logger.warning(f"Health: PostgreSQL FAIL — {e}")

    overall = "ok" if (qdrant_ok and ollama_ok and redis_ok and postgres_ok) else "degraded"

    return HealthResponse(
        status=overall,
        qdrant=qdrant_ok,
        ollama=ollama_ok,
        redis=redis_ok,
        postgres=postgres_ok,
        details=details if details else None,
    )