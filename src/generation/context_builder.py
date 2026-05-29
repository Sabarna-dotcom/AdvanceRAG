"""
ContextBuilder - formats retrieved chunks into a clean
context string with numbered source citations.
Handles both PDF and audio/transcript chunks.
"""

from typing import List, Dict, Optional

from src.utils.logger import get_logger
from src.utils.exceptions import ValidationException

logger = get_logger(__name__)

# Hard limit to stay within LLM context window
MAX_CONTEXT_CHARS = 6_000


class ContextBuilder:
    """
    Converts a list of retrieved chunks into a
    formatted context string and a citations map.
    """

    def __init__(self):
        logger.info("ContextBuilder initialized.")

    # ---------------------------------------------
    # Public API
    # ---------------------------------------------

    def build(
        self,
        chunks: List[Dict],
        max_chars: int = MAX_CONTEXT_CHARS,
    ) -> Dict:
        """
        Build context string + citations from retrieved chunks.

        Args:
            chunks:     List of chunk dicts from RetrievalManager.
            max_chars:  Maximum total characters for context (token guard).

        Returns:
            {
                "context":     str  - formatted context for the prompt,
                "citations":   list - [{index, source, page, timestamp, text}]
            }
        """

        if not chunks:
            logger.warning("ContextBuilder received empty chunks list.")
            return {"context": "No relevant context found.", "citations": []}

        formatted_parts = []
        citations = []
        total_chars = 0

        for i, chunk in enumerate(chunks, start=1):

            text = self._get_text(chunk)
            if not text:
                continue

            meta = chunk.get("metadata", {})
            source_label = self._format_source_label(i, meta)
            block = f"[Source {i}] - {source_label}\n\n{text}\n"

            if total_chars + len(block) > max_chars:
                logger.debug(
                    f"Context limit reached at chunk {i}, stopping."
                )
                break

            formatted_parts.append(block)
            total_chars += len(block)

            citations.append(
                self._build_citation(i, meta, text)
            )

        context_str = "\n".join(formatted_parts)

        logger.info(
            f"ContextBuilder: built context with "
            f"{len(citations)} sources, {total_chars} chars."
        )

        return {"context": context_str, "citations": citations}

    # ---------------------------------------------
    # Private Helpers
    # ---------------------------------------------

    def _get_text(self, chunk: Dict) -> str:
        """Extract text from chunk dict (handles different key names)."""
        return (
            chunk.get("text")
            or chunk.get("page_content")
            or chunk.get("content")
            or ""
        ).strip()

    def _format_source_label(self, index: int, meta: Dict) -> str:
        """
        Build a human-readable source label.

        Examples:
            PDF:   "10. Biotechnology and its Application.pdf"
            Audio: "Your First HTML Website, 04:32 - 06:15"
        """

        source_type = meta.get("source_type", "unknown")

        if source_type == "audio" or source_type == "transcript":
            title = meta.get("title") or meta.get("file_name") or "Unknown Audio"
            start = meta.get("start")
            end = meta.get("end")

            if start is not None and end is not None:
                return f"{title}, {self._format_timestamp(start)} - {self._format_timestamp(end)}"
            elif start is not None:
                return f"{title}, {self._format_timestamp(start)}"

            return title

        # PDF / default — use source_name (actual filename), fall back to title
        filename = (
                meta.get("source_name")
                or meta.get("file_name")
                or meta.get("title")
                or "Unknown PDF"
        )

        return filename

    def _format_timestamp(self, timestamp) -> str:
        """Convert seconds (float/int) or 'MM:SS' string to MM:SS."""
        try:
            if isinstance(timestamp, (int, float)):
                total_seconds = int(timestamp)
                minutes = total_seconds // 60
                seconds = total_seconds % 60
                return f"{minutes:02d}:{seconds:02d}"

            # already a string like '03:45'
            return str(timestamp)

        except Exception:
            return str(timestamp)

    def _build_citation(self, index: int, meta: Dict, text: str) -> Dict:
        """Build a structured citation object for post-processing."""

        source_type = meta.get("source_type", "unknown")

        # PDF: prefer source_name (actual filename)
        # Audio: prefer title (human-readable lecture name)
        if source_type in ("audio", "transcript"):
            display_title = (
                    meta.get("title")
                    or meta.get("file_name")
                    or "Unknown Audio"
            )
        else:
            display_title = (
                    meta.get("source_name")
                    or meta.get("file_name")
                    or meta.get("title")
                    or "Unknown PDF"
            )

        start = meta.get("start")
        end = meta.get("end")

        return {
            "index": index,
            "source_type": source_type,
            "title": display_title,
            "page": meta.get("page_number") or meta.get("page"),
            "start_time": self._format_timestamp(start) if start is not None else None,
            "end_time": self._format_timestamp(end) if end is not None else None,
            "chunk_id": meta.get("chunk_id") or meta.get("id"),
            "preview": text[:120],
        }