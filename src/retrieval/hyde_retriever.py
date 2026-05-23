"""
HyDE Retriever - Hypothetical Document Embedding.

Generates a fake answer to the query, embeds it,
then retrieves using that embedding for better semantic matching.

This `HyDERetriever` code implements Hypothetical Document Embedding (HyDE) retrieval in the RAG system.
Instead of directly searching using the user query, it first asks the LLM to generate a hypothetical answer or paragraph related to the query, then uses that generated text as the semantic search query for vector retrieval.
Since the hypothetical answer is usually closer in embedding space to real documents than the short user query itself, this approach improves semantic matching and helps retrieve more contextually relevant chunks from the vector database.

"""

from typing import List, Dict, Optional

from src.llm.llm_model import OllamaLLM
from src.retrieval.vector_retriever import VectorRetriever
from src.config.retrieval_config import (
    get_config as get_retrieval_config
)
from src.utils.logger import get_logger
from src.utils.exceptions import (
    LLMException,
    VectorStoreException
)

logger = get_logger(__name__)


class HyDERetriever:
    """
    Hypothetical Document Embedding (HyDE) retriever.

    Instead of embedding the query directly, it:

    1. Asks the LLM to generate a hypothetical answer
    2. Embeds that hypothetical answer
    3. Uses that embedding for retrieval

    This often finds more relevant documents because
    the fake answer is closer in embedding space to
    real documents than the raw question is.
    """

    def __init__(self):

        try:

            logger.info("Initializing HyDERetriever.")

            self.llm = OllamaLLM()

            self.vector_retriever = VectorRetriever()

            self.retrieval_config = (
                get_retrieval_config()
            )

            logger.info(
                "HyDERetriever initialized successfully."
            )

        except Exception as error:

            logger.exception(
                "HyDERetriever initialization failed."
            )

            raise LLMException(
                message="Failed to initialize HyDERetriever",
                details=str(error)
            ) from error

    def generate_hypothetical_answer(
        self,
        query: str
    ) -> str:
        """
        Use LLM to generate a plausible hypothetical
        answer for the query.
        """

        prompt = f"""
Write a short, factual paragraph that would answer the following question.

Write as if you are an expert writing study material.
Do not say you are generating a hypothetical answer.
Just write the answer directly.

Question: {query}

Answer:
"""

        try:

            response = self.llm.generate(prompt)

            logger.info(
                "Generated hypothetical answer."
            )

            return response.strip()

        except Exception as error:

            logger.warning(
                f"HyDE generation failed: {error}. "
                f"Using query directly."
            )

            return query

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        collection: Optional[str] = None,
    ) -> List[Dict]:
        """
        HyDE retrieval:

        1. Generate hypothetical answer
        2. Retrieve using that answer as the search query

        Args:

            query:
                Original user query

            top_k:
                Number of results

            collection:
                'pdf', 'audio', or None

        Returns:

            List of retrieved chunks
        """

        try:

            if not query or not query.strip():

                raise VectorStoreException(
                    message="Query cannot be empty"
                )

            top_k = (
                top_k
                or self.retrieval_config.top_k_initial
            )

            logger.info(
                f"HyDE retrieval for: {query[:60]}"
            )

            # Generate hypothetical answer
            hypothetical_answer = (
                self.generate_hypothetical_answer(query)
            )

            logger.info(
                f"Hypothetical answer: "
                f"{hypothetical_answer[:80]}..."
            )

            # Retrieve using hypothetical answer embedding
            results = self.vector_retriever.retrieve(
                query=hypothetical_answer,
                top_k=top_k,
                collection=collection,
            )

            # Tag results as coming from HyDE
            for result in results:

                result["retrieval_method"] = "hyde"

            logger.info(
                f"HyDE retrieval returned "
                f"{len(results)} results."
            )

            return results

        except (VectorStoreException, LLMException):

            raise

        except Exception as error:

            logger.exception(
                "HyDE retrieval failed."
            )

            raise VectorStoreException(
                message="HyDE retrieval failed",
                details=str(error)
            ) from error