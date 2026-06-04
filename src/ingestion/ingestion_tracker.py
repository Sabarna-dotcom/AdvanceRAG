# src/ingestion/ingestion_tracker.py
"""
IngestionTracker — tracks which files have been ingested and their content hash.

Stored as a JSON file (one per collection) at:
    data/processed/.ingestion_state_{collection}.json

Schema:
    {
      "filename.pdf": {
        "hash": "sha256hex",
        "chunk_ids": [0, 1, 2, ...],
        "ingested_at": "2026-06-04T10:00:00"
      },
      ...
    }

On each ingestion run:
  - NEW file      → embed + index, save state
  - CHANGED file  → delete old vectors, embed + index new, update state
  - DELETED file  → delete old vectors, remove from state
  - UNCHANGED     → skip entirely
"""

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Tuple

from src.utils.logger import get_logger

logger = get_logger(__name__)

_STATE_DIR = os.path.join("data", "processed")


class IngestionTracker:
    """
    Manages incremental ingestion state for a single Qdrant collection.

    Args:
        collection_name: e.g. "pdf_collection" or "audio_collection"
    """

    def _init_(self, collection_name: str):
        self.collection_name = collection_name
        self._state_path = os.path.join(
            _STATE_DIR, f".ingestion_state{collection_name}.json"
        )
        self._state: Dict[str, dict] = self._load()
        logger.info(
            f"IngestionTracker loaded | collection={collection_name} | "
            f"tracked_files={len(self._state)} | state_file={self._state_path}"
        )

    # ------------------------------------------
    # Public API
    # ------------------------------------------

    def compute_hash(self, file_path: str) -> str:
        """SHA-256 hash of a file's contents."""
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            for block in iter(lambda: f.read(65536), b""):
                h.update(block)
        return h.hexdigest()

    def is_new(self, filename: str) -> bool:
        """True if file has never been ingested."""
        return filename not in self._state

    def is_changed(self, filename: str, current_hash: str) -> bool:
        """True if file was ingested before but hash is different now."""
        if filename not in self._state:
            return False
        return self._state[filename]["hash"] != current_hash

    def get_chunk_ids(self, filename: str) -> List[str]:
        """Return previously stored Qdrant point IDs for this file."""
        return self._state.get(filename, {}).get("chunk_ids", [])

    def get_tracked_filenames(self) -> List[str]:
        """All filenames currently tracked."""
        return list(self._state.keys())

    def save_file_state(self, filename: str, file_hash: str, chunk_ids: List[int]):
        """Record that a file was successfully ingested."""
        self._state[filename] = {
            "hash": file_hash,
            "chunk_ids": chunk_ids,
            "ingested_at": datetime.now(timezone.utc).isoformat(),
        }
        self._persist()
        logger.info(
            f"IngestionTracker saved | file={filename} | chunks={len(chunk_ids)}"
        )

    def remove_file_state(self, filename: str):
        """Remove a file from tracking (after its vectors are deleted)."""
        if filename in self._state:
            del self._state[filename]
            self._persist()
            logger.info(f"IngestionTracker removed | file={filename}")

    def reset(self):
        """Wipe all tracked state — use after a full collection wipe."""
        self._state = {}
        self._persist()
        logger.info(f"IngestionTracker reset | collection={self.collection_name}")

    def diff(self, current_files: Dict[str, str]) -> Tuple[List[str], List[str], List[str]]:
        """
        Compare current files on disk against tracked state.

        Args:
            current_files: {filename: hash} of files currently on disk

        Returns:
            (new_files, changed_files, deleted_files)
        """
        tracked = set(self._state.keys())
        on_disk  = set(current_files.keys())

        new_files     = [f for f in on_disk  if f not in tracked]
        deleted_files = [f for f in tracked  if f not in on_disk]
        changed_files = [
            f for f in on_disk
            if f in tracked and self._state[f]["hash"] != current_files[f]
        ]

        return new_files, changed_files, deleted_files

    # ------------------------------------------
    # Internal
    # ------------------------------------------

    def _load(self) -> Dict[str, dict]:
        os.makedirs(_STATE_DIR, exist_ok=True)
        if not os.path.exists(self._state_path):
            return {}
        try:
            with open(self._state_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"IngestionTracker: failed to load state file — starting fresh. {e}")
            return {}

    def _persist(self):
        try:
            with open(self._state_path, "w", encoding="utf-8") as f:
                json.dump(self._state, f, indent=2)
        except Exception as e:
            logger.error(f"IngestionTracker: failed to persist state. {e}")

 