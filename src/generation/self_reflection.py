"""
SelfReflection — after an initial answer is generated,
asks the LLM to evaluate its own response quality.
If confidence is low, signals the pipeline to retrieve more context.
"""

import json

from typing import Dict, Optional

from src.generation.prompt_builder import PromptBuilder
from src.utils.logger import get_logger
from src.utils.exceptions import LLMException

logger = get_logger(__name__)

# Threshold below which we trigger corrective re-retrieval
LOW_CONFIDENCE_THRESHOLD = 0.55


class SelfReflection:
    """
    Uses the LLM to reflect on its own generated answer.

    Returns a structured assessment with a confidence score
    and a flag indicating whether more retrieval is needed.
    """

    def __init__(self, llm):
        """
        Args:
            llm: An instance of OllamaLLM
                 (or any object with .generate(prompt) -> str).
        """

        self.llm = llm
        self.prompt_builder = PromptBuilder()

        logger.info("SelfReflection initialized.")

    def reflect(
        self,
        query: str,
        answer: str,
        context: str,
    ) -> Dict:
        """
        Ask the LLM to evaluate the quality of the given answer.

        Args:
            query:   The original user question.
            answer:  The generated answer to evaluate.
            context: The context string that was used
                     to generate the answer.

        Returns:
            {
                "accuracy_confidence":      float,
                "completeness_confidence":  float,
                "citation_confidence":      float,
                "overall_confidence":       float,
                "uncertainties":            list[str],
                "needs_more_retrieval":     bool,
                "improvement_hint":         str,
                "reflection_error":         Optional[str]
            }
        """

        try:

            reflection_prompt = (
                self.prompt_builder.build_reflection_prompt(
                    query=query,
                    answer=answer,
                    context=context,
                )
            )

            raw = self.llm.generate(reflection_prompt)

            result = self._parse_reflection(raw)

            logger.info(
                f"SelfReflection: "
                f"overall_confidence="
                f"{result.get('overall_confidence')}, "
                f"needs_more_retrieval="
                f"{result.get('needs_more_retrieval')}"
            )

            return result

        except Exception as error:

            logger.warning(
                f"SelfReflection failed: {error}"
            )

            # Return safe defaults — don't crash pipeline
            return self._fallback_result(str(error))

    # -------------------------------------------------
    # Private Helpers
    # -------------------------------------------------

    def _parse_reflection(
        self,
        raw: str,
    ) -> Dict:
        """
        Parse the LLM's JSON reflection output.

        Handles cases where the LLM wraps JSON
        in markdown code blocks.
        """

        # Strip markdown fences if present
        text = raw.strip()

        if text.startswith("```"):

            lines = text.splitlines()

            text = "\n".join(
                line
                for line in lines
                if not line.strip().startswith("```")
            ).strip()

        try:

            data = json.loads(text)

        except json.JSONDecodeError:

            # Try extracting JSON substring
            start = text.find("{")
            end = text.rfind("}") + 1

            if start != -1 and end > start:

                data = json.loads(text[start:end])

            else:

                raise ValueError(
                    f"Could not parse reflection JSON: "
                    f"{text[:200]}"
                )

        # Normalize and fill defaults
        result = {
            "accuracy_confidence": float(
                data.get("accuracy_confidence", 0.5)
            ),
            "completeness_confidence": float(
                data.get("completeness_confidence", 0.5)
            ),
            "citation_confidence": float(
                data.get("citation_confidence", 0.5)
            ),
            "overall_confidence": float(
                data.get("overall_confidence", 0.5)
            ),
            "uncertainties": data.get(
                "uncertainties",
                [],
            ),
            "needs_more_retrieval": bool(
                data.get(
                    "needs_more_retrieval",
                    False,
                )
            ),
            "improvement_hint": data.get(
                "improvement_hint",
                "",
            ),
            "reflection_error": None,
        }

        # Auto-flag if confidence falls below threshold
        if (
            result["overall_confidence"]
            < LOW_CONFIDENCE_THRESHOLD
        ):
            result["needs_more_retrieval"] = True

        return result

    def _fallback_result(
        self,
        error_msg: str,
    ) -> Dict:
        """
        Safe defaults when reflection fails —
        do not trigger re-retrieval.
        """

        return {
            "accuracy_confidence": 0.5,
            "completeness_confidence": 0.5,
            "citation_confidence": 0.5,
            "overall_confidence": 0.5,
            "uncertainties": [],
            "needs_more_retrieval": False,
            "improvement_hint": "",
            "reflection_error": error_msg,
        }