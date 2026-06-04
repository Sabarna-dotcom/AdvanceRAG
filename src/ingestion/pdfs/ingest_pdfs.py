"""
PDF ingestion pipeline — incremental mode.

On each run:
  - NEW pdf      → process + embed + index
  - CHANGED pdf  → delete old vectors, process + embed + index new
  - DELETED pdf  → delete vectors from Qdrant, remove from tracker
  - UNCHANGED    → skip
"""

import json
import os

from src.embeddings.pdf_batch_embedder import PDFBatchEmbedder
from src.vectorstore.pdf_indexing import PDFIndexingManager
from src.ingestion.ingestion_tracker import IngestionTracker
from src.ingestion.pdfs.document_processor import DocumentProcessor
from src.utils.logger import get_logger
from src.config.ingestion_config import get_config
from src.utils.exceptions import LLMException

logger = get_logger(__name__)
config = get_config()

PDF_CHUNKS_PATH = os.path.join(
    config.paths.processed_pdf_dir, "chunks", "pdf_chunks.json"
)
RAW_PDF_DIR = config.paths.raw_pdf_dir
COLLECTION   = "pdf_collection"


# ==========================================
# Helpers
# ==========================================

def _scan_pdf_files() -> dict:
    """Return {filename: sha256_hash} for all PDFs in raw_pdf_dir."""
    tracker = IngestionTracker(COLLECTION)
    result  = {}
    if not os.path.isdir(RAW_PDF_DIR):
        logger.warning(f"Raw PDF dir not found: {RAW_PDF_DIR}")
        return result
    for fname in os.listdir(RAW_PDF_DIR):
        if fname.lower().endswith(".pdf"):
            fpath = os.path.join(RAW_PDF_DIR, fname)
            result[fname] = tracker.compute_hash(fpath)
    return result


def _process_and_embed(file_path: str) -> list:
    """Process a single PDF → chunks → embeddings."""
    processor = DocumentProcessor()
    chunks    = processor.process_pdf(file_path)
    if not chunks:
        return []
    embedder  = PDFBatchEmbedder()
    return embedder.generate_embeddings(chunks)


def load_pdf_chunks():
    """Legacy helper — loads pre-generated chunks JSON (used by API route)."""
    try:
        logger.info("Loading PDF chunks from JSON.")
        with open(PDF_CHUNKS_PATH, "r", encoding="utf-8") as f:
            chunks = json.load(f)
        logger.info(f"Loaded {len(chunks)} PDF chunks.")
        return chunks
    except Exception as error:
        logger.exception("Failed to load PDF chunks.")
        raise LLMException(
            message="Failed to load PDF chunks", details=str(error)
        ) from error


# ==========================================
# Incremental ingestion entry point
# ==========================================

def run_incremental_ingestion() -> dict:
    """
    Scan raw PDF directory, compare against tracker state, and:
      - index new files
      - re-index changed files (delete old vectors first)
      - delete vectors for removed files

    Returns a summary dict.
    """
    tracker  = IngestionTracker(COLLECTION)
    indexer  = PDFIndexingManager()
    on_disk  = _scan_pdf_files()

    new_files, changed_files, deleted_files = tracker.diff(on_disk)

    summary = {
        "new": [], "changed": [], "deleted": [], "skipped": [], "errors": []
    }

    # ------------------------------------------
    # Handle deleted files — remove from Qdrant
    # ------------------------------------------
    for fname in deleted_files:
        try:
            chunk_ids = tracker.get_chunk_ids(fname)
            if chunk_ids:
                indexer.vector_db.delete_by_ids(chunk_ids)
            else:
                # fallback: delete by metadata.source
                indexer.vector_db.delete_by_source(fname)
            tracker.remove_file_state(fname)
            summary["deleted"].append(fname)
            logger.info(f"Incremental PDF: deleted vectors for removed file '{fname}'.")
        except Exception as e:
            logger.error(f"Incremental PDF: failed to delete '{fname}': {e}")
            summary["errors"].append({"file": fname, "error": str(e)})

    # ------------------------------------------
    # Handle changed files — delete old, re-index
    # ------------------------------------------
    for fname in changed_files:
        try:
            chunk_ids = tracker.get_chunk_ids(fname)
            if chunk_ids:
                indexer.vector_db.delete_by_ids(chunk_ids)
            else:
                indexer.vector_db.delete_by_source(fname)

            fpath           = os.path.join(RAW_PDF_DIR, fname)
            embedded_chunks = _process_and_embed(fpath)

            if embedded_chunks:
                new_ids = indexer.index_chunks(embedded_chunks)
                tracker.save_file_state(fname, on_disk[fname], new_ids)
                summary["changed"].append(fname)
                logger.info(
                    f"Incremental PDF: re-indexed changed file '{fname}' "
                    f"({len(embedded_chunks)} chunks)."
                )
        except Exception as e:
            logger.error(f"Incremental PDF: failed to re-index '{fname}': {e}")
            summary["errors"].append({"file": fname, "error": str(e)})

    # ------------------------------------------
    # Handle new files — process + index
    # ------------------------------------------
    for fname in new_files:
        try:
            fpath           = os.path.join(RAW_PDF_DIR, fname)
            embedded_chunks = _process_and_embed(fpath)

            if embedded_chunks:
                new_ids = indexer.index_chunks(embedded_chunks)
                tracker.save_file_state(fname, on_disk[fname], new_ids)
                summary["new"].append(fname)
                logger.info(
                    f"Incremental PDF: indexed new file '{fname}' "
                    f"({len(embedded_chunks)} chunks)."
                )
        except Exception as e:
            logger.error(f"Incremental PDF: failed to index new file '{fname}': {e}")
            summary["errors"].append({"file": fname, "error": str(e)})

    # Unchanged files
    unchanged = [
        f for f in on_disk
        if f not in new_files and f not in changed_files
    ]
    summary["skipped"] = unchanged

    logger.info(
        f"Incremental PDF ingestion complete | "
        f"new={len(summary['new'])} changed={len(summary['changed'])} "
        f"deleted={len(summary['deleted'])} skipped={len(summary['skipped'])} "
        f"errors={len(summary['errors'])}"
    )
    return summary


def main():
    """CLI entry point — runs incremental ingestion."""
    summary = run_incremental_ingestion()
    print("\n=== PDF Incremental Ingestion Summary ===")
    print(f"  New      : {summary['new']}")
    print(f"  Changed  : {summary['changed']}")
    print(f"  Deleted  : {summary['deleted']}")
    print(f"  Skipped  : {len(summary['skipped'])} files (unchanged)")
    print(f"  Errors   : {summary['errors']}")


if __name__ == "__main__":
    main()

