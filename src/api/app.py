"""
FastAPI application entry point.

Startup:
    uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000

Docs:
    http://localhost:8000/docs       ← Swagger UI
    http://localhost:8000/redoc      ← ReDoc UI
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from src.api.routes import health, query, session, ingestion, cache
from src.api.routes import auth
from src.api.middleware.rate_limit import rate_limit_middleware
from src.api.middleware.error_handler import (
    global_exception_handler,
    llm_exception_handler,
    vectorstore_exception_handler,
)
from src.utils.exceptions import LLMException, VectorStoreException
from src.utils.logger import get_logger

# Prometheus instrumentation
try:
    from prometheus_fastapi_instrumentator import Instrumentator
    _PROMETHEUS_AVAILABLE = True
except ImportError:
    _PROMETHEUS_AVAILABLE = False

logger = get_logger(__name__)

# ==========================================
# App Initialization
# ==========================================

app = FastAPI(
    title="Advanced Educational RAG API",
    description=(
        "Production-grade Retrieval-Augmented Generation system "
        "for educational content (PDFs + Audio lectures). "
        "Supports hybrid retrieval, HyDE, fusion, adaptive strategies, "
        "self-reflection, and cited answers."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Prometheus metrics — auto-instruments all HTTP routes
# Exposes /metrics endpoint for Prometheus scraping
if _PROMETHEUS_AVAILABLE:
    Instrumentator(
        should_group_status_codes=False,
        should_ignore_untemplated=True,
        should_respect_env_var=False,
        should_instrument_requests_inprogress=True,
        excluded_handlers=["/metrics", "/docs", "/redoc", "/openapi.json"],
        inprogress_name="rag_http_requests_inprogress",
        inprogress_labels=True,
    ).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
    logger.info("Prometheus metrics instrumentation enabled at /metrics")

# ==========================================
# CORS Middleware
# Allows frontend / Postman to call the API
# ==========================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # Restrict this to specific domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# Rate Limit Middleware
# ==========================================

app.add_middleware(BaseHTTPMiddleware, dispatch=rate_limit_middleware)

# ==========================================
# Exception Handlers
# ==========================================

app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(LLMException, llm_exception_handler)
app.add_exception_handler(VectorStoreException, vectorstore_exception_handler)

# ==========================================
# Routes
# ==========================================

app.include_router(health.router,     tags=["Health"])
app.include_router(auth.router,       tags=["Auth"])
app.include_router(query.router,      tags=["Query"])
app.include_router(session.router,    tags=["Session"])
app.include_router(ingestion.router,  tags=["Ingestion"])
app.include_router(cache.router,      tags=["Cache"])

# ==========================================
# Startup / Shutdown Events
# ==========================================

@app.on_event("startup")
async def on_startup():
    logger.info("RAG API starting up...")


@app.on_event("shutdown")
async def on_shutdown():
    logger.info("RAG API shutting down...")


# ==========================================
# Root redirect to docs
# ==========================================

@app.get("/", include_in_schema=False)
async def root():
    return {"message": "RAG API is running. Visit /docs for the Swagger UI."}
