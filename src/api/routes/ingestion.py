"""
Ingestion routes — trigger PDF or audio ingestion pipelines via the API.

Routes:
    POST   /ingest/pdf      — run the PDF embedding + indexing pipeline (incremental)
    POST   /ingest/audio    — run the audio transcript embedding + indexing pipeline (incremental)
    POST   /ingest/all      — run both pipelines sequentially (incremental)
    POST   /ingest/reindex  — wipe ALL vectors + tracker state, then re-ingest everything fresh
    DELETE /ingest/wipe     — wipe ALL vectors + tracker state (without re-ingesting)
    DELETE /ingest/file     — delete a specific file's vectors from Qdrant + tracker
    GET    /ingest/status   — check what collections exist and their point counts
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
    pipeline: str = Field(...)
    status: Literal["success", "failed", "skipped"] = Field(...)
    chunks_indexed: int = Field(default=0)
    duration_seconds: float = Field(default=0.0)
    message: str = Field(default="")
    # incremental detail
    new_files: List[str]     = Field(default=[])
    changed_files: List[str] = Field(default=[])
    deleted_files: List[str] = Field(default=[])
    skipped_count: int       = Field(default=0)
    errors: List[dict]       = Field(default=[])


class IngestionResponse(BaseModel):
    results: List[IngestionResult] = Field(default=[])
    total_chunks_indexed: int = Field(default=0)
    overall_status: Literal["success", "partial", "failed"] = Field(...)


class CollectionInfo(BaseModel):
    name: str
    points: int


class IngestionStatusResponse(BaseModel):
    collections: List[CollectionInfo] = Field(default=[])
    qdrant_reachable: bool = Field(...)
    tracker_state: Optional[Dict] = Field(default=None)


class DeleteFileRequest(BaseModel):
    filename: str = Field(..., description="Exact filename (e.g. 'biotech.pdf') to remove from Qdrant.")
    collection: Literal["pdf", "audio"] = Field(..., description="'pdf' or 'audio'")


class DeleteFileResponse(BaseModel):
    filename: str
    collection: str
    message: str
    success: bool


# ==========================================
# Helpers
# ==========================================

def _run_pdf_pipeline() -> IngestionResult:
    start = time.time()
    try:
        logger.info("Ingestion API: starting incremental PDF pipeline.")
        from src.ingestion.pdfs.ingest_pdfs import run_incremental_ingestion
        summary  = run_incremental_ingestion()
        duration = round(time.time() - start, 2)
        total    = (
            len(summary["new"]) + len(summary["changed"])
        )
        return IngestionResult(
            pipeline="pdf",
            status="success",
            chunks_indexed=total,
            duration_seconds=duration,
            message=f"Incremental PDF done. new={len(summary['new'])} changed={len(summary['changed'])} deleted={len(summary['deleted'])} skipped={len(summary['skipped'])}",
            new_files=summary["new"],
            changed_files=summary["changed"],
            deleted_files=summary["deleted"],
            skipped_count=len(summary["skipped"]),
            errors=summary["errors"],
        )
    except Exception as exc:
        duration = round(time.time() - start, 2)
        logger.error(f"Ingestion API: PDF pipeline FAILED — {exc}")
        return IngestionResult(
            pipeline="pdf", status="failed",
            duration_seconds=duration, message=str(exc),
        )


def _run_audio_pipeline() -> IngestionResult:
    start = time.time()
    try:
        logger.info("Ingestion API: starting incremental audio pipeline.")
        from src.ingestion.audios.ingest_audios import run_incremental_ingestion
        summary  = run_incremental_ingestion()
        duration = round(time.time() - start, 2)
        total    = len(summary["new"]) + len(summary["changed"])
        return IngestionResult(
            pipeline="audio",
            status="success",
            chunks_indexed=total,
            duration_seconds=duration,
            message=f"Incremental audio done. new={len(summary['new'])} changed={len(summary['changed'])} deleted={len(summary['deleted'])} skipped={len(summary['skipped'])}",
            new_files=summary["new"],
            changed_files=summary["changed"],
            deleted_files=summary["deleted"],
            skipped_count=len(summary["skipped"]),
            errors=summary["errors"],
        )
    except Exception as exc:
        duration = round(time.time() - start, 2)
        logger.error(f"Ingestion API: audio pipeline FAILED — {exc}")
        return IngestionResult(
            pipeline="audio", status="failed",
            duration_seconds=duration, message=str(exc),
        )


def _build_response(results: List[IngestionResult]) -> IngestionResponse:
    total    = sum(r.chunks_indexed for r in results)
    statuses = {r.status for r in results}
    if statuses == {"success"}:
        overall = "success"
    elif statuses == {"failed"}:
        overall = "failed"
    else:
        overall = "partial"
    return IngestionResponse(
        results=results, total_chunks_indexed=total, overall_status=overall
    )


class WipeResponse(BaseModel):
    pdf_collection_wiped:   bool = Field(default=False)
    audio_collection_wiped: bool = Field(default=False)
    tracker_reset:          bool = Field(default=False)
    message:                str  = Field(default="")


# ==========================================
# Routes
# ==========================================

@router.post(
    "/ingest/pdf",
    response_model=IngestionResponse,
    summary="Incremental PDF Ingestion",
    description=(
        "Run incremental PDF ingestion. Only new or changed PDFs are processed. "
        "Deleted PDFs have their vectors removed from Qdrant automatically."
    ),
)
async def ingest_pdf() -> IngestionResponse:
    logger.info("POST /ingest/pdf — triggered.")
    return _build_response([_run_pdf_pipeline()])


@router.post(
    "/ingest/audio",
    response_model=IngestionResponse,
    summary="Incremental Audio Ingestion",
    description=(
        "Run incremental audio transcript ingestion. "
        "Only new or changed transcript JSONs are processed."
    ),
)
async def ingest_audio() -> IngestionResponse:
    logger.info("POST /ingest/audio — triggered.")
    return _build_response([_run_audio_pipeline()])


@router.post(
    "/ingest/all",
    response_model=IngestionResponse,
    summary="Incremental Ingestion — All",
    description="Run incremental ingestion for both PDF and audio collections.",
)
async def ingest_all() -> IngestionResponse:
    logger.info("POST /ingest/all — triggered.")
    return _build_response([_run_pdf_pipeline(), _run_audio_pipeline()])


@router.delete(
    "/ingest/file",
    response_model=DeleteFileResponse,
    summary="Delete File Vectors",
    description=(
        "Delete all Qdrant vectors for a specific file and remove it from the ingestion tracker. "
        "Use this when you manually delete a file and want vectors removed immediately."
    ),
)
async def delete_file_vectors(request: DeleteFileRequest) -> DeleteFileResponse:
    """Delete a specific file's vectors from Qdrant + tracker."""
    logger.info(f"DELETE /ingest/file | filename={request.filename} collection={request.collection}")
    try:
        from src.ingestion.ingestion_tracker import IngestionTracker
        from src.vectorstore.qdrant_manager import QdrantManager

        collection_name = "pdf_collection" if request.collection == "pdf" else "audio_collection"
        tracker = IngestionTracker(collection_name)
        qdrant  = QdrantManager(collection_name=collection_name)

        chunk_ids = tracker.get_chunk_ids(request.filename)
        if chunk_ids:
            qdrant.delete_by_ids(chunk_ids)
        else:
            qdrant.delete_by_source(request.filename)

        tracker.remove_file_state(request.filename)

        return DeleteFileResponse(
            filename=request.filename,
            collection=request.collection,
            message=f"Vectors deleted for '{request.filename}' from {collection_name}.",
            success=True,
        )
    except Exception as exc:
        logger.error(f"DELETE /ingest/file failed: {exc}")
        return DeleteFileResponse(
            filename=request.filename,
            collection=request.collection,
            message=str(exc),
            success=False,
        )


@router.get(
    "/ingest/status",
    response_model=IngestionStatusResponse,
    summary="Ingestion Status",
    description="Check Qdrant collections, point counts, and tracker state.",
)
async def ingest_status() -> IngestionStatusResponse:
    try:
        from qdrant_client import QdrantClient
        from src.config.vectorstore_config import get_config as get_vs_config
        from src.ingestion.ingestion_tracker import IngestionTracker

        vs_config = get_vs_config()
        client    = QdrantClient(host=vs_config.host, port=vs_config.port, timeout=5)
        collections_resp = client.get_collections()
        collections = [
            CollectionInfo(
                name=c.name,
                points=client.get_collection(c.name).points_count or 0,
            )
            for c in collections_resp.collections
        ]

        # Include tracker state summary
        pdf_tracker   = IngestionTracker("pdf_collection")
        audio_tracker = IngestionTracker("audio_collection")
        tracker_state = {
            "pdf_tracked_files":   len(pdf_tracker.get_tracked_filenames()),
            "audio_tracked_files": len(audio_tracker.get_tracked_filenames()),
            "pdf_files":           pdf_tracker.get_tracked_filenames(),
            "audio_files":         audio_tracker.get_tracked_filenames(),
        }

        logger.info(f"GET /ingest/status — {len(collections)} collections.")
        return IngestionStatusResponse(
            collections=collections, qdrant_reachable=True, tracker_state=tracker_state
        )
    except Exception as exc:
        logger.error(f"GET /ingest/status — error: {exc}")
        return IngestionStatusResponse(collections=[], qdrant_reachable=False)


# ==========================================
# Wipe helper — shared by DELETE and reindex
# ==========================================

def _wipe_all() -> WipeResponse:
    """
    Delete all points from both Qdrant collections
    and reset both tracker state files.
    """
    from src.vectorstore.qdrant_manager import QdrantManager
    from src.ingestion.ingestion_tracker import IngestionTracker

    pdf_wiped   = False
    audio_wiped = False
    tracker_ok  = False
    errors      = []

    # Wipe pdf_collection
    try:
        qdrant_pdf = QdrantManager(collection_name="pdf_collection")
        qdrant_pdf.client.delete_collection("pdf_collection")
        qdrant_pdf.create_collection()          # recreate empty
        pdf_wiped = True
        logger.info("Wiped pdf_collection from Qdrant.")
    except Exception as e:
        logger.error(f"Wipe pdf_collection failed: {e}")
        errors.append(f"pdf_collection: {e}")

    # Wipe audio_collection
    try:
        qdrant_audio = QdrantManager(collection_name="audio_collection")
        qdrant_audio.client.delete_collection("audio_collection")
        qdrant_audio.create_collection()        # recreate empty
        audio_wiped = True
        logger.info("Wiped audio_collection from Qdrant.")
    except Exception as e:
        logger.error(f"Wipe audio_collection failed: {e}")
        errors.append(f"audio_collection: {e}")

    # Reset tracker state files
    try:
        pdf_tracker   = IngestionTracker("pdf_collection")
        audio_tracker = IngestionTracker("audio_collection")
        pdf_tracker.reset()
        audio_tracker.reset()
        tracker_ok = True
        logger.info("Tracker state files reset.")
    except Exception as e:
        logger.error(f"Tracker reset failed: {e}")
        errors.append(f"tracker: {e}")

    msg = "All data wiped successfully." if not errors else f"Partial wipe. Errors: {errors}"
    return WipeResponse(
        pdf_collection_wiped=pdf_wiped,
        audio_collection_wiped=audio_wiped,
        tracker_reset=tracker_ok,
        message=msg,
    )


@router.delete(
    "/ingest/wipe",
    response_model=WipeResponse,
    summary="Wipe All Vectors",
    description=(
        "Delete ALL vectors from both Qdrant collections (pdf_collection + audio_collection) "
        "and reset both ingestion tracker state files. "
        "Does NOT re-ingest. Call POST /ingest/all afterwards to re-ingest from scratch, "
        "or use POST /ingest/reindex to wipe + re-ingest in one call."
    ),
)
async def wipe_all_vectors() -> WipeResponse:
    logger.info("DELETE /ingest/wipe — wiping all Qdrant data + tracker state.")
    return _wipe_all()


@router.post(
    "/ingest/reindex",
    response_model=IngestionResponse,
    summary="Full Re-index (Wipe + Re-ingest)",
    description=(
        "Wipe ALL existing vectors and tracker state, then immediately re-ingest "
        "all PDF and audio files from scratch. "
        "Use this when you want a completely clean re-index of all data."
    ),
)
async def reindex_all() -> IngestionResponse:
    logger.info("POST /ingest/reindex — full wipe + re-ingest triggered.")

    wipe = _wipe_all()
    if not wipe.pdf_collection_wiped or not wipe.audio_collection_wiped:
        # wipe failed — return early, don't re-ingest into broken state
        return IngestionResponse(
            results=[
                IngestionResult(
                    pipeline="wipe",
                    status="failed",
                    message=wipe.message,
                )
            ],
            total_chunks_indexed=0,
            overall_status="failed",
        )

    # Re-ingest everything fresh
    results = [_run_pdf_pipeline(), _run_audio_pipeline()]
    return _build_response(results)


