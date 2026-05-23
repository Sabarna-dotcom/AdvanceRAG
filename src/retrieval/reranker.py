"""
LLM-based reranker — reranks retrieved chunks by asking
Ollama LLM to score relevance of each (query, chunk) pair.
No PyTorch, no ONNX, no DLL issues — uses existing Ollama setup.

This code is an LLM-based reranker used in a RAG system. After retrieving chunks from a vector database like Qdrant,
it sends each query–chunk pair to an Ollama LLM and asks the model to score how relevant the chunk is to the user query.
The chunks are then sorted based on these relevance scores, and the top-ranked chunks are returned for final response generation.
This improves retrieval quality and answer accuracy without using heavy libraries like PyTorch or sentence-transformers.

"""

from typing import List, Dict, Optional

from src.llm.llm_model import OllamaLLM
from src.config.retrieval_config import get_config as get_retrieval_config
from src.utils.logger import get_logger
from src.utils.exceptions import VectorStoreException


logger = get_logger(__name__)


class Reranker:
    """
    Reranks retrieved chunks using Ollama LLM.

    For each chunk, asks the LLM to score how relevant
    the chunk is to the query (0.0 to 1.0).
    Sorts by that score and returns top_k.

    No PyTorch, no ONNX, no sentence-transformers needed.
    Uses the same Ollama instance already running.
    """

    def __init__(self):
        try:
            logger.info("Initializing Reranker (Ollama LLM).")

            self.retrieval_config = get_retrieval_config()
            self.llm = OllamaLLM()

            logger.info("Reranker initialized successfully (Ollama LLM).")

        except Exception as error:
            logger.exception("Reranker initialization failed.")

            raise VectorStoreException(
                message="Failed to initialize Reranker",
                details=str(error)
            ) from error

    def _score_chunk(self, query: str, chunk_text: str) -> float:
        """
        Ask LLM to score relevance of chunk to query.
        Returns a float between 0.0 and 1.0.
        """

        prompt = f"""
Rate how relevant the following text is to the question.
Reply with ONLY a number between 0 and 10. Nothing else.

Question: {query}

Text: {chunk_text[:500]}

Relevance score (0-10):
"""

        try:
            response = self.llm.generate(prompt).strip()

            # Parse the number from response
            for token in response.replace(",", " ").split():
                try:
                    score = float(token)

                    # Normalize to 0-1
                    return min(max(score / 10.0, 0.0), 1.0)

                except ValueError:
                    continue

            # If parsing fails return 0.5 (neutral)
            logger.warning(
                f"Could not parse score from LLM response: '{response}'"
            )

            return 0.5

        except Exception as e:
            logger.warning(f"LLM scoring failed for chunk: {e}")

            return 0.0

    def rerank(
        self,
        query: str,
        chunks: List[Dict],
        top_k: Optional[int] = None,
    ) -> List[Dict]:
        """
        Rerank chunks using Ollama LLM relevance scoring.

        Args:
            query: The user query
            chunks: List of retrieved chunks to rerank
            top_k: Number of top results to return

        Returns:
            Reranked list of chunks with 'rerank_score' field
        """

        try:
            if not chunks:
                logger.warning("No chunks to rerank.")
                return []

            if not query or not query.strip():
                raise VectorStoreException(
                    message="Query cannot be empty"
                )

            top_k = top_k or self.retrieval_config.top_k_final

            logger.info(
                f"Reranking {len(chunks)} chunks "
                f"for query: '{query[:60]}'"
            )

            # Score each chunk
            for chunk in chunks:
                chunk_text = chunk.get("text", "")

                score = self._score_chunk(query, chunk_text)

                chunk["rerank_score"] = score

            # Sort by rerank score descending
            reranked = sorted(
                chunks,
                key=lambda x: x.get("rerank_score", 0.0),
                reverse=True
            )

            final = reranked[:top_k]

            logger.info(
                f"Reranking complete. "
                f"Returning top {len(final)} chunks."
            )

            return final

        except VectorStoreException:
            raise

        except Exception as error:
            logger.exception("Reranking failed.")

            raise VectorStoreException(
                message="Reranking failed",
                details=str(error)
            ) from error