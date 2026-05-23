"""
Retrieval Manager — unified entry point for the
entire retrieval layer. Orchestrates all strategies
based on config flags and returns final reranked results.

This `RetrievalManager` code acts as the central controller of the entire RAG retrieval pipeline.
It first cleans and enriches the user query using `QueryProcessor`, then runs multiple retrieval strategies like adaptive retrieval, hybrid retrieval, HyDE retrieval, and fusion retrieval based on configuration settings.
After collecting results from all retrievers, it merges and removes duplicate chunks, optionally reranks them using a cross-encoder reranker for better relevance, and finally returns the top most relevant chunks.
It also supports query decomposition, where a complex query is broken into smaller sub-questions, retrieval is performed for each sub-query, and all results are merged and reranked to improve answer quality for complex questions.

"""

from typing import List, Dict, Optional

from src.retrieval.adaptive_retriever import AdaptiveRetriever
from src.retrieval.hybrid_retriever import HybridRetriever
from src.retrieval.hyde_retriever import HyDERetriever
from src.retrieval.fusion_retriever import FusionRetriever
from src.retrieval.reranker import Reranker
from src.retrieval.query_processor import QueryProcessor
from src.retrieval.query_decomposer import QueryDecomposer

from src.config.retrieval_config import (
    get_config as get_retrieval_config
)

from src.utils.logger import get_logger
from src.utils.exceptions import VectorStoreException

logger = get_logger(__name__)


class RetrievalManager:
    """
    Single unified entry point for retrieval.
    Decides which strategies to run based on config,
    merges results, reranks and returns final chunks.

    This is what the LangGraph workflow will call.
    """

    def __init__(self):
        try:
            logger.info("Initializing RetrievalManager.")

            self.config = get_retrieval_config()

            # Always available
            self.query_processor = QueryProcessor()
            self.adaptive_retriever = AdaptiveRetriever()
            self.hybrid_retriever = HybridRetriever()
            self.reranker = Reranker()

            # Optional strategies
            self.hyde_retriever = (
                HyDERetriever()
                if self.config.use_hyde
                else None
            )

            self.fusion_retriever = (
                FusionRetriever()
                if self.config.use_fusion
                else None
            )

            self.query_decomposer = QueryDecomposer()

            logger.info(
                "RetrievalManager initialized successfully."
            )

        except Exception as error:
            logger.exception(
                "RetrievalManager initialization failed."
            )

            raise VectorStoreException(
                message="Failed to initialize RetrievalManager",
                details=str(error)
            ) from error

    def _deduplicate(
        self,
        chunks: List[Dict]
    ) -> List[Dict]:
        """
        Remove duplicate chunks by chunk_id.
        """

        seen = set()
        unique = []

        for chunk in chunks:

            cid = (
                chunk.get("chunk_id")
                or chunk.get("text", "")[:80]
            )

            if cid not in seen:
                seen.add(cid)
                unique.append(chunk)

        return unique

    def retrieve(
        self,
        query: str,
        chat_history: Optional[list] = None,
        collection: Optional[str] = None,
        top_k: Optional[int] = None,
        use_reranker: bool = True,
    ) -> List[Dict]:
        """
        Full retrieval pipeline:

        1. Process query
        2. Run adaptive/hybrid retrieval
        3. Optionally run HyDE retrieval
        4. Optionally run Fusion retrieval
        5. Merge + deduplicate
        6. Rerank
        7. Return final results
        """

        try:

            if not query or not query.strip():
                raise VectorStoreException(
                    message="Query cannot be empty"
                )

            top_k_final = (
                top_k or self.config.top_k_final
            )

            top_k_initial = (
                self.config.top_k_initial
            )

            logger.info(
                f"RetrievalManager query='{query[:60]}' "
                f"top_k_final={top_k_final}"
            )

            # Step 1: Process query
            processed_query = (
                self.query_processor.process(
                    query=query,
                    chat_history=chat_history
                )
            )

            all_results = []

            # Step 2: Adaptive retrieval
            adaptive_results = (
                self.adaptive_retriever.retrieve(
                    query=processed_query,
                    collection=collection,
                )
            )

            all_results.extend(adaptive_results)

            # Step 3: HyDE retrieval
            if self.hyde_retriever:

                try:
                    hyde_results = (
                        self.hyde_retriever.retrieve(
                            query=query,
                            top_k=top_k_initial,
                            collection=collection,
                        )
                    )

                    all_results.extend(hyde_results)

                except Exception as e:
                    logger.warning(
                        f"HyDE retrieval failed: {e}"
                    )

            # Step 4: Fusion retrieval
            if self.fusion_retriever:

                try:
                    fusion_results = (
                        self.fusion_retriever.retrieve(
                            query=query,
                            top_k=top_k_initial,
                            collection=collection,
                        )
                    )

                    all_results.extend(fusion_results)

                except Exception as e:
                    logger.warning(
                        f"Fusion retrieval failed: {e}"
                    )

            if not all_results:
                logger.warning(
                    "No results retrieved from any strategy."
                )
                return []

            # Step 5: Deduplicate
            all_results = self._deduplicate(all_results)

            logger.info(
                f"Total unique results before reranking: "
                f"{len(all_results)}"
            )

            # Step 6: Rerank
            if (
                use_reranker
                and len(all_results) > top_k_final
            ):

                final_results = (
                    self.reranker.rerank(
                        query=query,
                        chunks=all_results,
                        top_k=top_k_final,
                    )
                )

            else:
                final_results = all_results[:top_k_final]

            logger.info(
                f"RetrievalManager returning "
                f"{len(final_results)} final results."
            )

            return final_results

        except VectorStoreException:
            raise

        except Exception as error:

            logger.exception(
                "RetrievalManager.retrieve() failed."
            )

            raise VectorStoreException(
                message="Retrieval pipeline failed",
                details=str(error)
            ) from error

    def retrieve_with_decomposition(
        self,
        query: str,
        collection: Optional[str] = None,
        top_k: Optional[int] = None,
    ) -> List[Dict]:
        """
        Retrieval with query decomposition.

        Decomposes query into sub-questions,
        retrieves for each,
        merges and reranks.
        """

        try:

            top_k_final = (
                top_k or self.config.top_k_final
            )

            # Decompose query
            sub_questions = (
                self.query_decomposer.decompose(query)
            )

            logger.info(
                f"Decomposed into "
                f"{len(sub_questions)} sub-questions."
            )

            all_results = []

            for sub_q in sub_questions:

                try:

                    results = (
                        self.hybrid_retriever.retrieve(
                            query=sub_q,
                            top_k=self.config.top_k_initial,
                            collection=collection,
                        )
                    )

                    all_results.extend(results)

                except Exception as e:

                    logger.warning(
                        f"Retrieval failed for "
                        f"sub-question: {e}"
                    )

                    continue

            if not all_results:
                return []

            # Deduplicate
            all_results = self._deduplicate(all_results)

            # Rerank using original query
            final_results = (
                self.reranker.rerank(
                    query=query,
                    chunks=all_results,
                    top_k=top_k_final,
                )
            )

            return final_results

        except Exception as error:

            logger.exception(
                "Retrieval with decomposition failed."
            )

            raise VectorStoreException(
                message="Decomposition retrieval failed",
                details=str(error)
            ) from error

