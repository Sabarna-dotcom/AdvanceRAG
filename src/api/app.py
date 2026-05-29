"""
FastAPI application entry point.

Startup:
    uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000

Docs:
    http://localhost:8000/docs   # Swagger UI
    http://localhost:8000/redoc  # ReDoc UI
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import health, query
from src.api.middleware.error_handler import (
    global_exception_handler,
    llm_exception_handler,
    vectorstore_exception_handler,
)

from src.utils.exceptions import LLMException, VectorStoreException
from src.utils.logger import get_logger

logger = get_logger(__name__)

# =====================================================
# App Initialization
# =====================================================

app = FastAPI(
    title="Advanced Educational RAG API",
    description=(
        "Production-grade Retrieval-Augmented Generation system "
        "for educational content (PDFs + Audio lectures). "
        "Supports hybrid retrieval, HyDE fusion, adaptive strategies, "
        "self-reflection, and cited answers."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# =====================================================
# CORS Middleware
# Allows frontend / Postman to call the API
# =====================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict this to specific domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================
# Exception Handlers
# =====================================================

app.add_exception_handler(
    Exception,
    global_exception_handler,
)

app.add_exception_handler(
    LLMException,
    llm_exception_handler,
)

app.add_exception_handler(
    VectorStoreException,
    vectorstore_exception_handler,
)

# =====================================================
# Routes
# =====================================================

app.include_router(
    health.router,
    tags=["Health"],
)

app.include_router(
    query.router,
    tags=["Query"],
)

# =====================================================
# Startup / Shutdown Events
# =====================================================

@app.on_event("startup")
async def on_startup():
    logger.info("RAG API starting up...")


@app.on_event("shutdown")
async def on_shutdown():
    logger.info("RAG API shutting down...")


# =====================================================
# Root redirect to docs
# =====================================================

@app.get("/", include_in_schema=False)
async def root():
    return {
        "message": "RAG API is running. Visit /docs for the Swagger UI."
    }