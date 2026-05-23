"""
Query processor - cleans, normalizes and enriches
the user query before retrieval.

This `QueryProcessor` code prepares and enriches user queries before retrieval in the RAG pipeline.
It first cleans and normalizes the query by removing unnecessary spaces, then injects recent chat history into the query so follow-up questions can retain conversational context.
By combining the current question with previous conversation turns, the system improves context understanding and helps the retriever fetch more accurate and relevant information for multi-turn conversations.

"""

from typing import Optional

from src.utils.logger import get_logger

logger = get_logger(__name__)


class QueryProcessor:
    """
    Handles query cleaning, normalization,
    and chat history context injection.
    """

    def __init__(self):

        logger.info(
            "QueryProcessor initialized."
        )

    def clean(
        self,
        query: str
    ) -> str:
        """
        Remove extra whitespace and normalize.
        """

        return " ".join(query.strip().split())

    def inject_history(
        self,
        query: str,
        chat_history: Optional[list] = None
    ) -> str:
        """
        Prepend recent chat history context to query
        so follow-up questions resolve correctly.
        """

        if not chat_history:

            return query

        recent = chat_history[-3:]  # last 3 turns

        context_lines = []

        for turn in recent:

            role = turn.get("role", "")

            content = turn.get("content", "")

            if role and content:

                context_lines.append(
                    f"{role}: {content}"
                )

        if not context_lines:

            return query

        context = "\n".join(context_lines)

        enriched = (
            f"[Context]\n{context}\n\n"
            f"[Question]\n{query}"
        )

        logger.info(
            "Injected chat history into query."
        )

        return enriched

    def process(
        self,
        query: str,
        chat_history: Optional[list] = None
    ) -> str:
        """
        Full processing pipeline:

        clean -> inject history.
        """

        query = self.clean(query)

        query = self.inject_history(
            query,
            chat_history
        )

        return query

