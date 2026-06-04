"""
Query processor — cleans, normalizes, rewrites and enriches
the user query before retrieval.
"""

from typing import Optional

from src.utils.logger import get_logger


logger = get_logger(__name__)

# ------------------------------------------------------------------
# Prompt used to rewrite a vague follow-up into a standalone query
# ------------------------------------------------------------------
_REWRITE_PROMPT = """You are a query rewriting assistant for a RAG system.

Given the recent conversation history and a follow-up question, rewrite the follow-up into a SINGLE clear, standalone question that can be understood WITHOUT the conversation history.

Rules:
- Resolve all pronouns (it, its, they, that, this, those) to their actual subject.
- Keep the rewritten question short and specific.
- If the question is ALREADY standalone and clear, return it UNCHANGED.
- Return ONLY the rewritten question — no explanation, no quotes, no prefix.

Conversation history:
{history}

Follow-up question: {query}

Rewritten standalone question:"""


class QueryProcessor:
    """
    Handles query cleaning, normalization, LLM-based rewriting
    and chat history context injection.

    Pipeline:
        clean → rewrite (LLM, if history exists) → inject history
    """

    def _init_(self):
        # LLM loaded lazily so QueryProcessor can init without Ollama
        self._llm = None
        logger.info("QueryProcessor initialized.")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _get_llm(self):
        """Lazy-load LLM to avoid circular imports and slow init."""
        if self._llm is None:
            from src.llm.llm_model import OllamaLLM
            self._llm = OllamaLLM()
        return self._llm

    @staticmethod
    def _is_followup(query: str) -> bool:
        """
        Quick heuristic — does this query LOOK like a follow-up?
        If yes, we call the LLM to rewrite it.
        If no, we skip the LLM call to save time.
        """
        followup_signals = [
            # pronouns
            " it ", " its ", " it?", " its?",
            " they ", " them ", " their ",
            " that ", " this ", " those ", " these ",
            " he ", " she ", " him ", " her ",
            # vague openers
            "what about", "how about", "tell me more",
            "explain more", "give more", "more details",
            "can you elaborate", "what else", "anything else",
            "why is that", "how does that", "what does that",
        ]
        q_lower = query.lower()
        # Also treat very short queries as likely follow-ups
        if len(query.split()) <= 4:
            return True
        return any(sig in q_lower for sig in followup_signals)

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def clean(self, query: str) -> str:
        """Remove extra whitespace and normalize."""
        return " ".join(query.strip().split())

    def rewrite(
        self,
        query: str,
        chat_history: Optional[list] = None,
    ) -> str:
        """
        Use the LLM to rewrite a vague follow-up question into a
        clear standalone question with all pronouns resolved.

        Only calls the LLM when:
        1. chat_history is present (there's context to resolve against)
        2. The query looks like a follow-up (has pronouns / vague openers)

        Returns the original query unchanged if rewriting is skipped
        or if the LLM call fails.

        Args:
            query:        The user's raw question.
            chat_history: Previous conversation turns [{role, content}].

        Returns:
            Rewritten standalone question string.
        """
        if not chat_history:
            return query

        if not self._is_followup(query):
            logger.debug("QueryProcessor: query looks standalone — skipping rewrite.")
            return query

        try:
            # Build a compact history string — last 4 turns max
            recent = chat_history[-4:]
            history_lines = []
            for turn in recent:
                role    = turn.get("role", "").capitalize()
                content = turn.get("content", "").strip()
                # Truncate long assistant answers to keep prompt short
                if role == "Assistant" and len(content) > 200:
                    content = content[:200] + "..."
                history_lines.append(f"{role}: {content}")
            history_str = "\n".join(history_lines)

            prompt = _REWRITE_PROMPT.format(
                history=history_str,
                query=query,
            )

            llm = self._get_llm()
            rewritten = llm.generate(prompt).strip()

            # Safety checks — if LLM returns something weird, use original
            if not rewritten or len(rewritten) > 300 or "\n" in rewritten:
                logger.warning(
                    f"QueryProcessor: rewrite result looks invalid — "
                    f"keeping original. Got: '{rewritten[:80]}'"
                )
                return query

            if rewritten.lower() == query.lower():
                logger.debug("QueryProcessor: rewrite unchanged — query was already standalone.")
                return query

            logger.info(
                f"QueryProcessor: query rewritten | "
                f"original='{query}' | rewritten='{rewritten}'"
            )
            return rewritten

        except Exception as e:
            # Never crash retrieval because of a rewrite failure
            logger.warning(f"QueryProcessor: rewrite failed — using original query. {e}")
            return query

    def inject_history(
        self,
        query: str,
        chat_history: Optional[list] = None,
    ) -> str:
        """
        Prepend recent chat history context to the (already rewritten) query
        so the retriever has extra signal for edge cases.
        """
        if not chat_history:
            return query

        recent = chat_history[-3:]  # last 3 turns
        context_lines = []

        for turn in recent:
            role    = turn.get("role", "")
            content = turn.get("content", "")
            if role and content:
                context_lines.append(f"{role}: {content[:150]}")

        if not context_lines:
            return query

        context  = "\n".join(context_lines)
        enriched = f"[Context]\n{context}\n\n[Question]\n{query}"

        logger.info("QueryProcessor: injected chat history into query.")
        return enriched

    def process(
        self,
        query: str,
        chat_history: Optional[list] = None,
    ) -> str:
        """
        Full processing pipeline:
            1. clean         — strip whitespace
            2. rewrite       — LLM resolves pronouns/vague refs (if follow-up)
            3. inject history — prepend context for retriever

        Args:
            query:        Raw user question.
            chat_history: Previous turns [{role, content}].

        Returns:
            Processed query string ready for Qdrant retrieval.
        """
        query = self.clean(query)
        query = self.rewrite(query, chat_history)
        query = self.inject_history(query, chat_history)
        return query