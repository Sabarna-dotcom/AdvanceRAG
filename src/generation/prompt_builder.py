"""
PromptBuilder — constructs all prompts used in the
generation layer (RAG answer, self-reflection, query rephrasing).
"""

from typing import List, Dict, Optional

from src.utils.logger import get_logger

logger = get_logger(__name__)


# =====================================================
# System Prompt Templates
# =====================================================

RAG_SYSTEM_PROMPT = """You are an expert educational assistant helping students understand complex topics.

Your job is to answer the student's question using ONLY the provided context from course materials.

Guidelines:
1. Answer clearly and educationally — explain concepts, don't just quote.
2. Cite every factual claim with [Source N] where N is the source number given in the context.
3. For audio/video sources, include the timestamp if available, e.g. [Source 2 - 03:45].
4. If the context does not contain enough information to answer, say: "I don't have enough information in the provided materials to answer this."
5. Do NOT make up facts outside the context.
6. Keep the answer focused and concise unless the question asks for detail.
"""

SELF_REFLECTION_SYSTEM_PROMPT = """You are a critical evaluator reviewing a question-answer pair.
Your task is to objectively assess the quality of the answer based on the provided context.
Return ONLY valid JSON — no markdown, no explanation outside the JSON.
"""

REPHRASE_SYSTEM_PROMPT = """You are a query rewriting assistant.
Rewrite the given query to be clearer and more specific for document retrieval.
Return ONLY the rewritten query — no explanation.
"""


class PromptBuilder:
    """
    Builds prompts for every stage of the generation pipeline.
    """

    def __init__(self):
        logger.info("PromptBuilder initialized.")

    def build_rag_prompt(
        self,
        query: str,
        context: str,
        chat_history: Optional[List[Dict]] = None,
    ) -> str:
        """
        Build the full RAG prompt for answer generation.

        Args:
            query:          The student's question.
            context:        Formatted context string from ContextBuilder.
            chat_history:   Optional list of previous turns [{role, content}].

        Returns:
            Full prompt string ready for the LLM.
        """

        history_section = ""

        if chat_history:

            history_lines = []

            for turn in chat_history[-6:]:  # last 3 exchanges

                role = turn.get("role", "user").capitalize()

                content = turn.get("content", "").strip()

                history_lines.append(f"{role}: {content}")

            history_section = (
                "\n=== PREVIOUS CONVERSATION ===\n"
                + "\n".join(history_lines)
                + "\n"
            )

        prompt = (
            f"{RAG_SYSTEM_PROMPT}\n\n"
            f"=== CONTEXT FROM SOURCES ===\n\n"
            f"{context}\n"
            f"{history_section}\n"
            f"=== STUDENT QUESTION ===\n"
            f"{query}\n\n"
            f"=== YOUR ANSWER ===\n"
        )

        logger.debug("RAG prompt built successfully.")

        return prompt

    def build_reflection_prompt(
        self,
        query: str,
        answer: str,
        context: str,
    ) -> str:
        """
        Build a self-reflection prompt to assess answer quality.
        Expects the LLM to return structured JSON.
        """

        prompt = (
            f"{SELF_REFLECTION_SYSTEM_PROMPT}\n\n"
            f"Question: {query}\n\n"
            f"Answer Given:\n{answer}\n\n"
            f"Context Used:\n{context[:3000]}\n\n"
            f"Evaluate the answer and return this exact JSON:\n"
            "{\n"
            '  "accuracy_confidence": <float 0.0-1.0>,\n'
            '  "completeness_confidence": <float 0.0-1.0>,\n'
            '  "citation_confidence": <float 0.0-1.0>,\n'
            '  "overall_confidence": <float 0.0-1.0>,\n'
            '  "uncertainties": [<string>, ...],\n'
            '  "needs_more_retrieval": <true or false>,\n'
            '  "improvement_hint": "<one sentence>"\n'
            "}\n"
        )

        return prompt

    def build_rephrase_prompt(self, query: str) -> str:
        """Build a prompt to rephrase a query for better retrieval."""

        return (
            f"{REPHRASE_SYSTEM_PROMPT}\n\n"
            f"Original query: {query}\n\n"
            f"Rewritten query:"
        )