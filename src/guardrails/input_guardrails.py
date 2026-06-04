# src/guardrails/input_guardrails.py
"""
InputGuardrails — validates the incoming query BEFORE it hits the RAG pipeline.

Checks:
  1. Query length (min / max)
  2. Prompt injection detection  — catches "ignore instructions", jailbreak patterns
  3. Content filter              — catches offensive / harmful queries

All checks are rule-based (no LLM call) so they are fast and free.
"""

import re
from dataclasses import dataclass
from typing import Optional

from src.config.guardrails_config import get_config
from src.utils.logger import get_logger

logger = get_logger(__name__)


# ==========================================
# Result dataclass
# ==========================================

@dataclass
class GuardrailResult:
    """Returned by every guardrail check."""
    passed: bool
    reason: Optional[str] = None   # human-readable rejection reason


# ==========================================
# Prompt Injection Patterns
# ==========================================

_INJECTION_PATTERNS = [
    # Classic ignore-instructions
    r"ignore\s+(all\s+)?(previous|prior|above|system)\s+instructions?",
    r"disregard\s+(all\s+)?(previous|prior|above|system)\s+instructions?",
    r"forget\s+(everything|all|your\s+instructions?)",

    # Role-play jailbreaks
    r"you\s+are\s+now\s+(dan|jailbreak|evil|free)",
    r"pretend\s+(you\s+are|to\s+be)\s+(an?\s+)?(evil|uncensored|unrestricted)",
    r"act\s+as\s+(if\s+you\s+(have\s+no|don.t\s+have)\s+restrictions?)",
    r"do\s+anything\s+now",
    r"developer\s+mode",

    # System prompt leaking
    r"repeat\s+(your\s+)?(system|initial)\s+prompt",
    r"reveal\s+(your\s+)?(system|initial|hidden)\s+(prompt|instructions?)",
    r"print\s+(your\s+)?(system|initial)\s+(prompt|instructions?)",

    # Prompt delimiter tricks
    r"----+\s*(system|user|assistant)",
    r"\[INST\]|\[/INST\]|<\|system\|>|<\|user\|>",
]

_INJECTION_REGEX = [re.compile(p, re.IGNORECASE) for p in _INJECTION_PATTERNS]


# ==========================================
# Content Filter — Banned Keywords
# ==========================================

_BANNED_KEYWORDS = [
    # Violence
    "how to kill", "how to murder", "how to make a bomb",
    "how to make explosives", "how to poison",
    # Self harm
    "how to commit suicide", "how to self harm",
    # Illegal
    "how to hack", "how to crack passwords", "how to ddos",
    "how to make drugs", "how to synthesize meth",
    # Explicit
    "child porn", "cp porn", "underage sex",
]


# ==========================================
# InputGuardrails
# ==========================================

class InputGuardrails:
    """
    Validates a query before it enters the RAG pipeline.

    Usage:
        guard = InputGuardrails()
        result = guard.check("What is photosynthesis?")
        if not result.passed:
            raise HTTPException(400, result.reason)
    """

    def _init_(self):
        self.config = get_config().input
        logger.info("InputGuardrails initialized.")

    # ------------------------------------------
    # Public entry point
    # ------------------------------------------

    def check(self, query: str) -> GuardrailResult:
        """
        Run all enabled input checks.
        Returns on first failure — fast exit.
        """
        result = self._check_length(query)
        if not result.passed:
            return result

        if self.config.enable_prompt_injection_detection:
            result = self._check_injection(query)
            if not result.passed:
                return result

        if self.config.enable_content_filter:
            result = self._check_content(query)
            if not result.passed:
                return result

        return GuardrailResult(passed=True)

    # ------------------------------------------
    # Check 1: Length
    # ------------------------------------------

    def _check_length(self, query: str) -> GuardrailResult:
        stripped = query.strip()
        length = len(stripped)

        if length < self.config.min_query_length:
            logger.warning(f"InputGuardrail: query too short ({length} chars).")
            return GuardrailResult(
                passed=False,
                reason=f"Query is too short. Minimum {self.config.min_query_length} characters required.",
            )

        if length > self.config.max_query_length:
            logger.warning(f"InputGuardrail: query too long ({length} chars).")
            return GuardrailResult(
                passed=False,
                reason=f"Query is too long. Maximum {self.config.max_query_length} characters allowed.",
            )

        return GuardrailResult(passed=True)

    # ------------------------------------------
    # Check 2: Prompt Injection
    # ------------------------------------------

    def _check_injection(self, query: str) -> GuardrailResult:
        for pattern in _INJECTION_REGEX:
            if pattern.search(query):
                logger.warning(
                    f"InputGuardrail: prompt injection detected. "
                    f"Pattern='{pattern.pattern[:50]}' query='{query[:80]}'"
                )
                return GuardrailResult(
                    passed=False,
                    reason="Query contains disallowed instructions. Please ask a genuine question.",
                )
        return GuardrailResult(passed=True)

    # ------------------------------------------
    # Check 3: Content Filter
    # ------------------------------------------

    def _check_content(self, query: str) -> GuardrailResult:
        query_lower = query.lower()
        for keyword in _BANNED_KEYWORDS:
            if keyword in query_lower:
                logger.warning(
                    f"InputGuardrail: banned content detected. "
                    f"keyword='{keyword}' query='{query[:80]}'"
                )
                return GuardrailResult(
                    passed=False,
                    reason="Query contains content that cannot be processed.",
                )
        return GuardrailResult(passed=True)