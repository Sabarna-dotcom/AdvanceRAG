"""
Audio embedding + indexing pipeline — incremental mode.

On each run:
  - NEW transcript JSON      → embed + index
  - CHANGED transcript JSON  → delete old vectors, embed + index new
  - DELETED transcript JSON  → delete vectors from Qdrant
  - UNCHANGED                → skip
"""

import os
import json

from src.embeddings.audio_batch_embedder import AudioBatchEmbedder
from src.vectorstore.audio_indexing import AudioIndexingManager
from src.ingestion.ingestion_tracker import IngestionTracker
from src.utils.logger import get_logger
from src.config.ingestion_config import get_config
from src.utils.exceptions import LLMException, VectorStoreException

logger = get_logger(__name__)
config = get_config()

TRANSCRIPT_DIRECTORY = config.paths.processed_transcript_dir
COLLECTION           = "audio_collection"


# ==========================================
# Helpers
# ==========================================

def _scan_transcript_files() -> dict:
    """Return {filename: sha256_hash} for all transcript JSONs."""
    tracker = IngestionTracker(COLLECTION)
    result  = {}
    if not os.path.isdir(TRANSCRIPT_DIRECTORY):
        logger.warning(f"Transcript dir not found: {TRANSCRIPT_DIRECTORY}")
        return result
    for fname in os.listdir(TRANSCRIPT_DIRECTORY):
        if fname.endswith(".json"):
            fpath = os.path.join(TRANSCRIPT_DIRECTORY, fname)
            result[fname] = tracker.compute_hash(fpath)
    return result


def _load_and_embed(file_path: str) -> list:
    """Load chunks from a transcript JSON and embed them."""
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    chunks = data.get("chunks", [])
    if not chunks:
        return []
    embedder = AudioBatchEmbedder()
    return embedder.generate_embeddings(chunks)


def load_transcript_chunks():
    """Legacy helper — loads all transcript chunks from all JSON files."""
    try:
        all_chunks = []
        logger.info("Loading transcript JSON files.")
        for fname in os.listdir(TRANSCRIPT_DIRECTORY):
            if fname.endswith(".json"):
                fpath = os.path.join(TRANSCRIPT_DIRECTORY, fname)
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                all_chunks.extend(data.get("chunks", []))
        logger.info(f"Loaded {len(all_chunks)} transcript chunks.")
        return all_chunks
    except Exception as error:
        logger.exception("Failed to load transcript chunks.")
        raise LLMException(
            message="Failed to load audio transcript chunks",
            details=str(error),
        ) from error


# ==========================================
# Incremental ingestion entry point
# ==========================================

def run_incremental_ingestion() -> dict:
    """
    Scan transcript directory, compare against tracker state, and:
      - index new transcript files
      - re-index changed transcript files (delete old vectors first)
      - delete vectors for removed transcript files

    Returns a summary dict.
    """
    tracker = IngestionTracker(COLLECTION)
    indexer = AudioIndexingManager()
    on_disk = _scan_transcript_files()

    new_files, changed_files, deleted_files = tracker.diff(on_disk)

    summary = {
        "new": [], "changed": [], "deleted": [], "skipped": [], "errors": []
    }

    # ------------------------------------------
    # Handle deleted files
    # ------------------------------------------
    for fname in deleted_files:
        try:
            chunk_ids = tracker.get_chunk_ids(fname)
            if chunk_ids:
                indexer.vector_db.delete_by_ids(chunk_ids)
            else:
                indexer.vector_db.delete_by_source(fname)
            tracker.remove_file_state(fname)
            summary["deleted"].append(fname)
            logger.info(f"Incremental Audio: deleted vectors for removed file '{fname}'.")
        except Exception as e:
            logger.error(f"Incremental Audio: failed to delete '{fname}': {e}")
            summary["errors"].append({"file": fname, "error": str(e)})

    # ------------------------------------------
    # Handle changed files
    # ------------------------------------------
    for fname in changed_files:
        try:
            chunk_ids = tracker.get_chunk_ids(fname)
            if chunk_ids:
                indexer.vector_db.delete_by_ids(chunk_ids)
            else:
                indexer.vector_db.delete_by_source(fname)

            fpath           = os.path.join(TRANSCRIPT_DIRECTORY, fname)
            embedded_chunks = _load_and_embed(fpath)

            if embedded_chunks:
                new_ids = indexer.index_chunks(embedded_chunks)
                tracker.save_file_state(fname, on_disk[fname], new_ids)
                summary["changed"].append(fname)
                logger.info(
                    f"Incremental Audio: re-indexed changed file '{fname}' "
                    f"({len(embedded_chunks)} chunks)."
                )
        except Exception as e:
            logger.error(f"Incremental Audio: failed to re-index '{fname}': {e}")
            summary["errors"].append({"file": fname, "error": str(e)})

    # ------------------------------------------
    # Handle new files
    # ------------------------------------------
    for fname in new_files:
        try:
            fpath           = os.path.join(TRANSCRIPT_DIRECTORY, fname)
            embedded_chunks = _load_and_embed(fpath)

            if embedded_chunks:
                new_ids = indexer.index_chunks(embedded_chunks)
                tracker.save_file_state(fname, on_disk[fname], new_ids)
                summary["new"].append(fname)
                logger.info(
                    f"Incremental Audio: indexed new file '{fname}' "
                    f"({len(embedded_chunks)} chunks)."
                )
        except Exception as e:
            logger.error(f"Incremental Audio: failed to index new file '{fname}': {e}")
            summary["errors"].append({"file": fname, "error": str(e)})

    unchanged = [
        f for f in on_disk
        if f not in new_files and f not in changed_files
    ]
    summary["skipped"] = unchanged

    logger.info(
        f"Incremental Audio ingestion complete | "
        f"new={len(summary['new'])} changed={len(summary['changed'])} "
        f"deleted={len(summary['deleted'])} skipped={len(summary['skipped'])} "
        f"errors={len(summary['errors'])}"
    )
    return summary


def main():
    """CLI entry point."""
    summary = run_incremental_ingestion()
    print("\n=== Audio Incremental Ingestion Summary ===")
    print(f"  New      : {summary['new']}")
    print(f"  Changed  : {summary['changed']}")
    print(f"  Deleted  : {summary['deleted']}")
    print(f"  Skipped  : {len(summary['skipped'])} files (unchanged)")
    print(f"  Errors   : {summary['errors']}")


if _name_ == "_main_":
    main()



def load_transcript_chunks():
    """
    Load all transcript chunks
    from transcript JSON files.
    """

    try:

        all_chunks = []

        logger.info(
            "Loading transcript JSON files."
        )

        for file_name in os.listdir(
            TRANSCRIPT_DIRECTORY
        ):

            if file_name.endswith(".json"):

                file_path = os.path.join(
                    TRANSCRIPT_DIRECTORY,
                    file_name
                )

                logger.info(
                    f"Loading transcript: "
                    f"{file_name}"
                )

                with open(
                    file_path,
                    "r",
                    encoding="utf-8"
                ) as file:

                    data = json.load(file)

                transcript_chunks = (
                    data.get("chunks", [])
                )

                all_chunks.extend(
                    transcript_chunks
                )

        logger.info(
            f"Loaded "
            f"{len(all_chunks)} "
            f"transcript chunks."
        )

        return all_chunks

    except Exception as error:

        logger.exception(
            "Failed to load transcript "
            "chunks."
        )

        raise LLMException(

            message=(
                "Failed to load "
                "audio transcript chunks"
            ),

            details=str(error)

        ) from error


def main():

    try:

        logger.info(
            "Starting audio ingestion."
        )

        transcript_chunks = (
            load_transcript_chunks()
        )

        embedder = (
            AudioBatchEmbedder()
        )

        embedded_chunks = (
            embedder.generate_embeddings(
                transcript_chunks
            )
        )

        indexer = (
            AudioIndexingManager()
        )

        indexer.index_chunks(
            embedded_chunks
        )

        logger.info(
            "Audio ingestion completed."
        )

    except (
        LLMException,
        VectorStoreException
    ):

        raise

    except Exception as error:

        logger.exception(
            "Audio ingestion pipeline failed."
        )

        raise Exception(

            f"Audio ingestion failed: "
            f"{error}"

        ) from error


if __name__ == "__main__":

    main()
 