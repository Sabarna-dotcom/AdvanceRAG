"""
GenerationManager — the main entry point for the generation layer.

Pipeline:
1. ContextBuilder   -> format retrieved chunks into numbered context
2. PromptBuilder    -> build full RAG prompt
3. OllamaLLM        -> generate answer
4. ResponseParser   -> extract answer + cited sources
5. SelfReflection   -> (optional) assess confidence
6. Corrective loop  -> if low confidence, retrieve more and regenerate (max 2 iterations)

This is what LangGraph nodes / the API layer will call.
"""

from typing import List, Dict, Optional

from src.generation.context_builder import ContextBuilder
from src.generation.prompt_builder import PromptBuilder
from src.generation.response_parser import ResponseParser
from src.generation.self_reflection import SelfReflection
from src.llm.llm_model import OllamaLLM
from src.utils.logger import get_logger
from src.utils.exceptions import LLMException

logger = get_logger(__name__)

# Maximum self-reflection / corrective iterations
MAX_ITERATIONS = 2


class GenerationManager:
    """
    Orchestrates the full generation pipeline:
    context formatting -> prompting -> LLM -> parsing -> reflection.
    """

    def __init__(self, use_self_reflection: bool = True):
        """
        Args:
            use_self_reflection: Whether to run self-reflection after generation.
                                 Set False to speed things up in testing.
        """

        try:
            logger.info("Initializing GenerationManager.")

            self.llm = OllamaLLM()
            self.context_builder = ContextBuilder()
            self.prompt_builder = PromptBuilder()
            self.response_parser = ResponseParser()

            self.self_reflection = (
                SelfReflection(self.llm)
                if use_self_reflection
                else None
            )

            self.use_self_reflection = use_self_reflection

            logger.info("GenerationManager initialized successfully.")

        except Exception as error:
            logger.exception("GenerationManager initialization failed.")

            raise LLMException(
                message="GenerationManager init failed",
                details=str(error),
            ) from error

    # -------------------------------------------------
    # Main Public Method
    # -------------------------------------------------

    def generate(
        self,
        query: str,
        chunks: List[Dict],
        chat_history: Optional[List[Dict]] = None,
        retriever=None,  # Optional RetrievalManager for corrective loop
        collection: Optional[str] = None,
    ) -> Dict:
        """
        Generate a final answer given a query and retrieved chunks.

        Args:
            query:          User's question.
            chunks:         Retrieved chunks from RetrievalManager.
            chat_history:   Optional conversation history [{role, content}].
            retriever:      Optional RetrievalManager instance for corrective re-retrieval.
            collection:     Qdrant collection to search ('pdf', 'audio', or None).

        Returns:
            {
                "answer":         str,
                "cited_sources":  list[dict],
                "cited_indices":  list[int],
                "has_answer":     bool,
                "reflection":     dict or None,
                "iterations":     int,
            }
        """

        try:

            if not query or not query.strip():
                raise LLMException(message="Query cannot be empty")

            if not chunks:
                logger.warning(
                    "GenerationManager: no chunks provided, returning no-answer."
                )
                return self._no_answer_response(query)

            iteration = 0
            current_chunks = chunks
            reflection_result = None

            while iteration < MAX_ITERATIONS:

                iteration += 1

                logger.info(
                    f"Generation iteration {iteration}/{MAX_ITERATIONS}"
                )

                # Step 1: Build context
                context_data = self.context_builder.build(current_chunks)

                context_str = context_data["context"]
                citations_map = context_data["citations"]

                # Step 2: Build prompt
                prompt = self.prompt_builder.build_rag_prompt(
                    query=query,
                    context=context_str,
                    chat_history=chat_history,
                )

                # Step 3: Generate
                raw_answer = self.llm.generate(prompt)

                # Step 4: Parse
                parsed = self.response_parser.parse(
                    raw_response=raw_answer,
                    citations_map=citations_map,
                )

                # Step 5: Self-reflection
                if self.use_self_reflection and self.self_reflection:

                    reflection_result = self.self_reflection.reflect(
                        query=query,
                        answer=parsed["answer"],
                        context=context_str,
                    )

                    needs_more = reflection_result.get(
                        "needs_more_retrieval",
                        False,
                    )

                    if (
                        needs_more
                        and retriever
                        and iteration < MAX_ITERATIONS
                    ):

                        logger.info(
                            f"Low confidence detected, triggering corrective retrieval "
                            f"(iteration {iteration})."
                        )

                        try:
                            extra_chunks = retriever.retrieve(
                                query=query,
                                chat_history=chat_history,
                                collection=collection,
                                top_k=20,
                                use_reranker=True,
                            )

                            # Merge original + new, deduplicate by chunk id
                            current_chunks = self._merge_chunks(
                                current_chunks,
                                extra_chunks,
                            )

                            continue  # loop again with richer context

                        except Exception as e:
                            logger.warning(
                                f"Corrective retrieval failed: {e}"
                            )

                # No more iterations needed
                break

            logger.info(
                f"GenerationManager complete: "
                f"has_answer={parsed['has_answer']}, "
                f"iterations={iteration}"
            )

            return {
                "answer": parsed["answer"],
                "cited_sources": parsed["cited_sources"],
                "cited_indices": parsed["cited_indices"],
                "has_answer": parsed["has_answer"],
                "reflection": reflection_result,
                "iterations": iteration,
            }

        except LLMException:
            raise

        except Exception as error:

            logger.exception("GenerationManager.generate() failed.")

            raise LLMException(
                message="Generation pipeline failed",
                details=str(error),
            ) from error

    # -------------------------------------------------
    # Convenience: generate with built-in retrieval
    # -------------------------------------------------

    def generate_with_retrieval(
        self,
        query: str,
        chat_history: Optional[List[Dict]] = None,
        collection: Optional[str] = None,
        top_k: int = 10,
    ) -> Dict:
        """
        Full RAG pipeline in one call: retrieve + generate.
        Useful for quick tests and the API layer.

        Lazily imports RetrievalManager to avoid circular imports.
        """

        from src.retrieval.retrieval_manager import RetrievalManager

        retriever = RetrievalManager()

        chunks = retriever.retrieve(
            query=query,
            chat_history=chat_history,
            collection=collection,
            top_k=top_k,
        )

        return self.generate(
            query=query,
            chunks=chunks,
            chat_history=chat_history,
            retriever=retriever,
            collection=collection,
        )

    # -------------------------------------------------
    # Private Helpers
    # -------------------------------------------------

    def _merge_chunks(
        self,
        original: List[Dict],
        extra: List[Dict],
    ) -> List[Dict]:
        """
        Merge two chunk lists, deduplicating by chunk_id or text prefix.
        """

        seen = set()
        merged = []

        for chunk in original + extra:

            key = (
                chunk.get("chunk_id")
                or chunk.get("metadata", {}).get("chunk_id")
                or (chunk.get("text", "")[:80])
            )

            if key not in seen:
                seen.add(key)
                merged.append(chunk)

        return merged

    def _no_answer_response(self, query: str) -> Dict:

        return {
            "answer": (
                "I don't have enough information in the provided "
                "materials to answer this question."
            ),
            "cited_sources": [],
            "cited_indices": [],
            "has_answer": False,
            "reflection": None,
            "iterations": 0,
        }


# =====================================================
# Quick smoke test
# =====================================================

if __name__ == "__main__":

    import json

    query = "Tell about Biotechnology and it's application."

    print(f"Query: {query}")
    print("Running full RAG pipeline...\n")

    manager = GenerationManager(use_self_reflection=False)

    result = manager.generate_with_retrieval(query=query)

    print("Answer:")
    print(result["answer"])

    print("\nCited Sources:")
    for src in result["cited_sources"]:
        source_type = src.get("source_type", "unknown")

        if source_type in ("audio", "transcript"):
            start = src.get("start_time", "")
            end = src.get("end_time", "")
            time_str = f"{start} - {end}" if start and end else start or ""

            print(f"  [{src['index']}] {src['title']} - {time_str}")
        else:
            print(f"  [{src['index']}] {src['title']}")

    print(f"\nHas Answer: {result['has_answer']}")
    print(f"Iterations: {result['iterations']}")