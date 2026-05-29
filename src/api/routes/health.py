"""
Health check route.
GET /health - checks if Qdrant and Ollama are reachable.
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
    description="Check if Qdrant and Ollama are reachable.",
)
async def health_check() -> HealthResponse:
    """
    Ping Qdrant and Ollama to verify the system is healthy.
    Returns overall status as 'ok' or 'degraded'.
    """

    qdrant_ok = False
    ollama_ok = False
    details = {}

    # --- Check Qdrant ---
    try:
        from qdrant_client import QdrantClient
        from src.config.vectorstore_config import get_config as get_vs_config

        vs_config = get_vs_config()

        client = QdrantClient(
            host=vs_config.host,
            port=vs_config.port,
            timeout=3,
        )

        client.get_collections()

        qdrant_ok = True
        logger.info("Health check: Qdrant OK.")

    except Exception as e:
        details["qdrant_error"] = str(e)
        logger.warning(f"Health check: Qdrant FAIL - {e}")

    # --- Check Ollama ---
    try:
        import requests as req
        from src.config.llm_config import get_config as get_llm_config

        llm_config = get_llm_config()

        resp = req.get(
            f"{llm_config.ollama_base_url}",
            timeout=3,
        )

        ollama_ok = resp.status_code == 200

        logger.info("Health check: Ollama OK.")

    except Exception as e:
        details["ollama_error"] = str(e)
        logger.warning(f"Health check: Ollama FAIL - {e}")

    overall = (
        "ok"
        if (qdrant_ok and ollama_ok)
        else "degraded"
    )

    return HealthResponse(
        status=overall,
        qdrant=qdrant_ok,
        ollama=ollama_ok,
        details=details if details else None,
    )