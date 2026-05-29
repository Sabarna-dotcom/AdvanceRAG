"""
ResponseParser — parses the raw LLM output.
Extracts the answer text, citations referenced in the response,
and builds a structured final response object.
"""

import re

from typing import List, Dict, Optional

from src.utils.logger import get_logger

logger = get_logger(__name__)

# Matches patterns like:
# [Source 1], [Source 3 - Page 5], [Source 2 - 04:32]
CITATION_PATTERN = re.compile(
    r"\[Source\s+(\d+)(?:[^\]]*)?\]",
    re.IGNORECASE,
)


class ResponseParser:
    """
    Parses raw LLM output into a structured response dict.
    """

    def __init__(self):
        logger.info("ResponseParser initialized.")

    def parse(
        self,
        raw_response: str,
        citations_map: Optional[List[Dict]] = None,
    ) -> Dict:
        """
        Parse raw LLM response.

        Args:
            raw_response:  The raw string returned by the LLM.
            citations_map: The citations list from ContextBuilder.build().

        Returns:
            {
                "answer":         str  - cleaned answer text,
                "cited_indices":  list - [1, 3, 5, ...] source numbers used,
                "cited_sources":  list - full citation dicts for used sources,
                "raw_response":   str  - original LLM output,
                "has_answer":     bool - False if LLM said it doesn't know,
            }
        """

        if not raw_response or not raw_response.strip():

            logger.warning(
                "ResponseParser received empty response."
            )

            return self._empty_response()

        answer = raw_response.strip()

        # Extract citation indices mentioned in the answer
        cited_indices = self._extract_citation_indices(answer)

        # Match to full citation objects
        cited_sources = []

        if citations_map:

            index_to_citation = {
                c["index"]: c for c in citations_map
            }

            for idx in cited_indices:

                if idx in index_to_citation:
                    cited_sources.append(index_to_citation[idx])

        # Detect "I don't know" type responses
        has_answer = not self._is_no_answer(answer)

        logger.info(
            f"ResponseParser: cited_indices={cited_indices}, "
            f"has_answer={has_answer}"
        )

        return {
            "answer": answer,
            "cited_indices": cited_indices,
            "cited_sources": cited_sources,
            "raw_response": raw_response,
            "has_answer": has_answer,
        }

    # -------------------------------------------------
    # Private Helpers
    # -------------------------------------------------

    def _extract_citation_indices(
        self,
        text: str,
    ) -> List[int]:
        """
        Find all [Source N] references in text,
        return sorted unique list.
        """

        matches = CITATION_PATTERN.findall(text)

        return sorted(set(int(m) for m in matches))

    def _is_no_answer(
        self,
        text: str,
    ) -> bool:
        """
        Detect if the LLM said it could not answer.
        """

        no_answer_phrases = [
            "don't have enough information",
            "not enough information",
            "cannot answer",
            "no information",
            "not mentioned in",
            "not provided in",
            "context does not",
            "materials do not",
        ]

        lower = text.lower()

        return any(
            phrase in lower
            for phrase in no_answer_phrases
        )

    def _empty_response(self) -> Dict:

        return {
            "answer": "",
            "cited_indices": [],
            "cited_sources": [],
            "raw_response": "",
            "has_answer": False,
        }