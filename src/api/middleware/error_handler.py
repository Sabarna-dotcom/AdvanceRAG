"""
Global error handler middleware.
Catches all unhandled exceptions and returns clean JSON error responses.
"""

from fastapi import Request
from fastapi.responses import JSONResponse

from src.utils.exceptions import LLMException, VectorStoreException
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def global_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """Catch-all handler for any unhandled exception."""

    logger.exception(
        f"Unhandled exception on {request.method} {request.url.path}"
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred.",
            "details": str(exc),
        },
    )


async def llm_exception_handler(
    request: Request,
    exc: LLMException
) -> JSONResponse:
    """Handle LLM / generation layer errors."""

    logger.error(
        f"LLMException on {request.url.path}: {exc}"
    )

    return JSONResponse(
        status_code=503,
        content={
            "error": "llm_error",
            "message": str(exc),
            "details": getattr(exc, "details", None),
        },
    )


async def vectorstore_exception_handler(
    request: Request,
    exc: VectorStoreException
) -> JSONResponse:
    """Handle Qdrant / vector store errors."""

    logger.error(
        f"VectorStoreException on {request.url.path}: {exc}"
    )

    return JSONResponse(
        status_code=503,
        content={
            "error": "vectorstore_error",
            "message": str(exc),
            "details": getattr(exc, "details", None),
        },
    )