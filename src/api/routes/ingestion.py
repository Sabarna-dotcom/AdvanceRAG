"""
Ingestion routes — trigger PDF or audio ingestion pipelines via the API.

Routes:
    POST /ingest/pdf   — run the PDF embedding + indexing pipeline
    POST /ingest/audio — run the audio transcript embedding + indexing pipeline
    POST /ingest/all   — run both pipelines sequentially
    GET  /ingest/status — check what collections exist and their point counts
"""

import time
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Literal

from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ==========================================
# Response Models
# ==========================================

class IngestionResult(BaseModel):
    """Result of a single ingestion run (PDF or audio)."""
    pipeline: str = Field(..., description="'pdf' or 'audio'.")
    status: Literal["success", "failed", "skipped"] = Field(..., description="Outcome of the pipeline.")
    chunks_indexed: int = Field(default=0, description="Number of chunks written to Qdrant.")
    duration_seconds: float = Field(default=0.0, description="Time taken in seconds.")
    message: str = Field(default="", description="Human-readable summary or error.")


class IngestionResponse(BaseModel):
    """Response for POST /ingest/* endpoints."""
    results: List[IngestionResult] = Field(default=[], description="Per-pipeline results.")
    total_chunks_indexed: int = Field(default=0, description="Grand total chunks indexed.")
    overall_status: Literal["success", "partial", "failed"] = Field(
        ..., description="'success' all passed | 'partial' one failed | 'failed' all failed."
    )


class CollectionInfo(BaseModel):
    name: str
    points: int


class IngestionStatusResponse(BaseModel):
    """Response for GET /ingest/status."""
    collections: List[CollectionInfo] = Field(default=[], description="Qdrant collections and point counts.")
    qdrant_reachable: bool = Field(..., description="True if Qdrant responded.")


# ==========================================
# Helpers
# ==========================================

def _run_pdf_pipeline() -> IngestionResult:
    """Run the PDF embedding + Qdrant indexing pipeline inline (mirrors ingest_pdfs.main)."""
    start = time.time()
    try:
        logger.info("Ingestion API: starting PDF pipeline.")
        from src.ingestion.pdfs.ingest_pdfs import load_pdf_chunks
        from src.embeddings.pdf_batch_embedder import PDFBatchEmbedder
        from src.vectorstore.pdf_indexing import PDFIndexingManager

        chunks = load_pdf_chunks()
        embedded = PDFBatchEmbedder().generate_embeddings(chunks)
        PDFIndexingManager().index_chunks(embedded)
        count = len(embedded) if embedded else 0

        duration = round(time.time() - start, 2)
        logger.info(f"Ingestion API: PDF pipeline complete | chunks={count} | duration={duration}s")
        return IngestionResult(
            pipeline="pdf",
            status="success",
            chunks_indexed=count,
            duration_seconds=duration,
            message=f"PDF ingestion completed. {count} chunks indexed.",
        )
    except Exception as exc:
        duration = round(time.time() - start, 2)
        logger.error(f"Ingestion API: PDF pipeline FAILED — {exc}")
        return IngestionResult(
            pipeline="pdf",
            status="failed",
            chunks_indexed=0,
            duration_seconds=duration,
            message=str(exc),
        )


def _run_audio_pipeline() -> IngestionResult:
    """Run the audio transcript embedding + Qdrant indexing pipeline inline (mirrors ingest_audios.main)."""
    start = time.time()
    try:
        logger.info("Ingestion API: starting audio pipeline.")
        from src.ingestion.audios.ingest_audios import load_transcript_chunks
        from src.embeddings.audio_batch_embedder import AudioBatchEmbedder
        from src.vectorstore.audio_indexing import AudioIndexingManager

        chunks = load_transcript_chunks()
        embedded = AudioBatchEmbedder().generate_embeddings(chunks)
        AudioIndexingManager().index_chunks(embedded)
        count = len(embedded) if embedded else 0

        duration = round(time.time() - start, 2)
        logger.info(f"Ingestion API: audio pipeline complete | chunks={count} | duration={duration}s")
        return IngestionResult(
            pipeline="audio",
            status="success",
            chunks_indexed=count,
            duration_seconds=duration,
            message=f"Audio ingestion completed. {count} chunks indexed.",
        )
    except Exception as exc:
        duration = round(time.time() - start, 2)
        logger.error(f"Ingestion API: audio pipeline FAILED — {exc}")
        return IngestionResult(
            pipeline="audio",
            status="failed",
            chunks_indexed=0,
            duration_seconds=duration,
            message=str(exc),
        )


def _build_response(results: List[IngestionResult]) -> IngestionResponse:
    """Compute totals and overall_status from a list of results."""
    total = sum(r.chunks_indexed for r in results)
    statuses = {r.status for r in results}
    if statuses == {"success"}:
        overall = "success"
    elif statuses == {"failed"}:
        overall = "failed"
    else:
        overall = "partial"
    return IngestionResponse(
        results=results,
        total_chunks_indexed=total,
        overall_status=overall,
    )


# ==========================================
# Routes
# ==========================================

@router.post(
    "/ingest/pdf",
    response_model=IngestionResponse,
    summary="Ingest PDFs",
    description=(
        "Run the PDF embedding and Qdrant indexing pipeline. "
        "Reads processed PDF chunks from disk, embeds them via bge-m3, "
        "and upserts into the 'pdf_collection' in Qdrant."
    ),
)
async def ingest_pdf() -> IngestionResponse:
    """Trigger the PDF ingestion pipeline synchronously."""
    logger.info("POST /ingest/pdf — triggered.")
    result = _run_pdf_pipeline()
    return _build_response([result])


@router.post(
    "/ingest/audio",
    response_model=IngestionResponse,
    summary="Ingest Audio Transcripts",
    description=(
        "Run the audio transcript embedding and Qdrant indexing pipeline. "
        "Reads processed transcript JSON files from disk, embeds them via bge-m3, "
        "and upserts into the 'audio_collection' in Qdrant."
    ),
)
async def ingest_audio() -> IngestionResponse:
    """Trigger the audio ingestion pipeline synchronously."""
    logger.info("POST /ingest/audio — triggered.")
    result = _run_audio_pipeline()
    return _build_response([result])


@router.post(
    "/ingest/all",
    response_model=IngestionResponse,
    summary="Ingest All (PDF + Audio)",
    description=(
        "Run both the PDF and audio ingestion pipelines sequentially. "
        "Useful for a full re-index of all content."
    ),
)
async def ingest_all() -> IngestionResponse:
    """Trigger both ingestion pipelines sequentially."""
    logger.info("POST /ingest/all — triggered.")
    results = [_run_pdf_pipeline(), _run_audio_pipeline()]
    return _build_response(results)


@router.get(
    "/ingest/status",
    response_model=IngestionStatusResponse,
    summary="Ingestion Status",
    description="Check Qdrant collections and their current point counts.",
)
async def ingest_status() -> IngestionStatusResponse:
    """Return collection names and point counts from Qdrant."""
    try:
        from qdrant_client import QdrantClient
        from src.config.vectorstore_config import get_config as get_vs_config
        vs_config = get_vs_config()
        client = QdrantClient(host=vs_config.host, port=vs_config.port, timeout=5)
        collections_resp = client.get_collections()
        collections = [
            CollectionInfo(
                name=c.name,
                points=client.get_collection(c.name).points_count or 0,
            )
            for c in collections_resp.collections
        ]
        logger.info(f"GET /ingest/status — {len(collections)} collections found.")
        return IngestionStatusResponse(collections=collections, qdrant_reachable=True)
    except Exception as exc:
        logger.error(f"GET /ingest/status — Qdrant error: {exc}")
        return IngestionStatusResponse(collections=[], qdrant_reachable=False)