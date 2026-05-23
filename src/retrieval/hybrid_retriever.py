"""
Hybrid retriever - combines vector (semantic) search
with BM25 keyword search using Reciprocal Rank Fusion (RRF).


This `HybridRetriever` code improves retrieval quality in your RAG system by combining semantic vector search with BM25 keyword-based search.
First, it retrieves semantically relevant chunks from the vector database using embeddings, then applies BM25 ranking on those retrieved chunks to find strong keyword matches.
After that, it merges both vector and keyword search results using Reciprocal Rank Fusion (RRF), which boosts chunks that rank well in both methods.
This hybrid approach helps the system retrieve more accurate and contextually relevant information by combining semantic understanding with exact keyword matching.

"""

from typing import List, Dict, Optional

from rank_bm25 import BM25Okapi

from src.retrieval.vector_retriever import VectorRetriever
from src.config.retrieval_config import (
    get_config as get_retrieval_config
)
from src.utils.logger import get_logger
from src.utils.exceptions import VectorStoreException

logger = get_logger(__name__)


class HybridRetriever:

    def __init__(self):

        try:

            logger.info("Initializing HybridRetriever.")

            self.vector_retriever = VectorRetriever()

            self.retrieval_config = get_retrieval_config()

            self.vector_weight = (
                self.retrieval_config.vector_weight
            )

            self.keyword_weight = (
                self.retrieval_config.keyword_weight
            )

            logger.info(
                "HybridRetriever initialized successfully."
            )

        except Exception as error:

            logger.exception(
                "HybridRetriever initialization failed."
            )

            raise VectorStoreException(
                message="Failed to initialize HybridRetriever",
                details=str(error)
            ) from error

    def reciprocal_rank_fusion(
        self,
        result_lists: List[List[Dict]],
        k: int = 60
    ) -> List[Dict]:

        scores = {}

        chunk_map = {}

        for result_list in result_lists:

            for rank, result in enumerate(
                result_list,
                start=1
            ):

                chunk_id = (
                    result.get("chunk_id")
                    or result.get("text", "")[:50]
                )

                if chunk_id not in scores:

                    scores[chunk_id] = 0.0

                    chunk_map[chunk_id] = result

                scores[chunk_id] += 1.0 / (k + rank)

        sorted_ids = sorted(
            scores.keys(),
            key=lambda cid: scores[cid],
            reverse=True
        )

        fused = []

        for cid in sorted_ids:

            result = chunk_map[cid].copy()

            result["rrf_score"] = scores[cid]

            fused.append(result)

        return fused

    def bm25_search(
        self,
        query: str,
        corpus: List[Dict],
        top_k: int
    ) -> List[Dict]:

        if not corpus:

            return []

        tokenized_corpus = [
            doc["text"].lower().split()
            for doc in corpus
            if doc.get("text")
        ]

        tokenized_query = query.lower().split()

        bm25 = BM25Okapi(tokenized_corpus)

        scores = bm25.get_scores(tokenized_query)

        scored = []

        for idx, doc in enumerate(corpus):

            if idx < len(scores):

                result = doc.copy()

                result["bm25_score"] = float(scores[idx])

                scored.append(result)

        return sorted(
            scored,
            key=lambda x: x["bm25_score"],
            reverse=True
        )[:top_k]

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        collection: Optional[str] = None,
    ) -> List[Dict]:

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
                f"Hybrid retrieval for: {query[:60]}"
            )

            vector_results = (
                self.vector_retriever.retrieve(
                    query=query,
                    top_k=top_k * 2,
                    collection=collection
                )
            )

            if not vector_results:

                logger.warning(
                    "Vector search returned no results."
                )

                return []

            bm25_results = self.bm25_search(
                query=query,
                corpus=vector_results,
                top_k=top_k
            )

            fused = self.reciprocal_rank_fusion(
                result_lists=[
                    vector_results,
                    bm25_results
                ]
            )

            final = fused[:top_k]

            logger.info(
                f"Hybrid retrieval returned "
                f"{len(final)} results."
            )

            return final

        except VectorStoreException:

            raise

        except Exception as error:

            logger.exception(
                "Hybrid retrieval failed."
            )

            raise VectorStoreException(
                message="Hybrid retrieval failed",
                details=str(error)
            ) from error