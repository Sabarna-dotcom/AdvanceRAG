# src/guardrails/output_guardrails.py
"""
OutputGuardrails — validates the LLM answer AFTER generation.

Checks:
  1. Hallucination detection  — answer must be grounded in retrieved chunks
  2. Citation validation      — every [Source N] must map to a real chunk

No external LLM call — purely local text overlap scoring (fast).
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from src.config.guardrails_config import get_config
from src.utils.logger import get_logger

logger = get_logger(__name__)


# ==========================================
# Result dataclass
# ==========================================

@dataclass
class OutputGuardrailResult:
    passed: bool
    reason: Optional[str] = None
    hallucination_score: float = 0.0          # 0.0 = fully grounded, 1.0 = no grounding
    invalid_citations: List[int] = field(default_factory=list)   # [Source N] numbers that are invalid
    warnings: List[str] = field(default_factory=list)


# ==========================================
# OutputGuardrails
# ==========================================

class OutputGuardrails:
    """
    Validates the generated answer against retrieved source chunks.

    Usage:
        guard = OutputGuardrails()
        result = guard.check(
            answer="Photosynthesis is the process...",
            chunks=[{"text": "...", "index": 1}, ...]
        )
        if not result.passed:
            # flag or regenerate
    """

    def _init_(self):
        self.config = get_config().output
        logger.info("OutputGuardrails initialized.")

    # ------------------------------------------
    # Public entry point
    # ------------------------------------------

    def check(
        self,
        answer: str,
        chunks: List[Dict[str, Any]],
    ) -> OutputGuardrailResult:
        """
        Run all enabled output checks.

        Args:
            answer : generated LLM answer string
            chunks : list of retrieved chunk dicts — each must have 'text' key
                     and optionally 'index' (1-based citation number)
        """
        result = OutputGuardrailResult(passed=True)

        if not answer or not answer.strip():
            result.passed = False
            result.reason = "Empty answer generated."
            return result

        # No chunks — nothing to validate against
        if not chunks:
            logger.warning("OutputGuardrail: no chunks provided, skipping grounding check.")
            return result

        if self.config.enable_hallucination_detection:
            score = self._hallucination_score(answer, chunks)
            result.hallucination_score = score

            if score > self.config.hallucination_threshold:
                result.warnings.append(
                    f"Answer may not be fully grounded in sources "
                    f"(hallucination_score={score:.2f}, threshold={self.config.hallucination_threshold})."
                )
                logger.warning(
                    f"OutputGuardrail: high hallucination score "
                    f"score={score:.2f} threshold={self.config.hallucination_threshold}"
                )

        if self.config.enable_citation_validation:
            invalid = self._validate_citations(answer, chunks)
            result.invalid_citations = invalid

            if invalid:
                result.warnings.append(
                    f"Answer references non-existent source(s): {invalid}."
                )
                logger.warning(
                    f"OutputGuardrail: invalid citations found: {invalid}"
                )

        return result

    # ------------------------------------------
    # Check 1: Hallucination Score
    # Token overlap between answer and all chunks combined.
    # Score = 1 - (overlap_ratio)  →  0 means fully grounded.
    # ------------------------------------------

    def _hallucination_score(
        self,
        answer: str,
        chunks: List[Dict[str, Any]],
    ) -> float:
        """
        Simple token overlap scoring.
        Measures what fraction of unique answer tokens appear in the retrieved chunks.
        Score close to 0 = well grounded. Score close to 1 = possibly hallucinated.
        """
        answer_tokens = self._tokenize(answer)
        if not answer_tokens:
            return 0.0

        # Combine all chunk texts
        all_chunk_text = " ".join(c.get("text", "") for c in chunks)
        chunk_tokens   = self._tokenize(all_chunk_text)

        if not chunk_tokens:
            return 1.0  # no source text — assume worst case

        overlap = answer_tokens & chunk_tokens
        overlap_ratio = len(overlap) / len(answer_tokens)

        # Invert: high overlap = low hallucination score
        score = round(1.0 - overlap_ratio, 4)
        logger.debug(
            f"OutputGuardrail hallucination_score={score} "
            f"answer_tokens={len(answer_tokens)} overlap={len(overlap)}"
        )
        return score

    # ------------------------------------------
    # Check 2: Citation Validation
    # Find all [Source N] references in the answer,
    # verify each N exists in the provided chunks.
    # ------------------------------------------

    def _validate_citations(
        self,
        answer: str,
        chunks: List[Dict[str, Any]],
    ) -> List[int]:
        """
        Returns list of citation numbers that appear in the answer
        but do NOT correspond to any real chunk.
        """
        # Extract all [Source N] references
        cited_numbers = set(
            int(m) for m in re.findall(r"\[Source\s+(\d+)]", answer, re.IGNORECASE)
        )

        if not cited_numbers:
            return []   # no citations at all — nothing to validate

        # Valid indices — use 'index' field if present, else derive from position
        valid_indices = set()
        for i, chunk in enumerate(chunks):
            idx = chunk.get("index", i + 1)
            valid_indices.add(int(idx))

        invalid = sorted(cited_numbers - valid_indices)
        return invalid

    # ------------------------------------------
    # Helpers
    # ------------------------------------------

    def _tokenize(self, text: str) -> set:
        """
        Lowercase word tokenizer — strips punctuation, returns set of tokens.
        Filters stop words and very short tokens for meaningful overlap scoring.
        """
        _STOP = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "shall", "can",
            "to", "of", "in", "for", "on", "with", "at", "by", "from",
            "and", "or", "but", "not", "it", "its", "this", "that",
            "these", "those", "as", "into", "through", "during", "before",
            "after", "above", "below", "between", "each", "than", "so",
        }
        tokens = re.findall(r"\b[a-z]{3,}\b", text.lower())
        return set(t for t in tokens if t not in _STOP)

 