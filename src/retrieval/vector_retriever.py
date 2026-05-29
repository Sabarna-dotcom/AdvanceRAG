"""
Vector retriever - queries Qdrant using
embedding similarity for both PDF and audio collections.

This code implements a `VectorRetriever` class that performs semantic search on stored PDF and audio embeddings using Qdrant vector database.
It first converts the user query into an embedding using the `OllamaEmbeddingModel`, then searches one or both Qdrant collections (`pdf` and `audio`) for the most similar chunks based on vector similarity.
The retrieved results contain chunk text, metadata, scores, and source type. The code also supports filtering results, sorting them by relevance score, and returning only the top-k matches.
Additionally, it provides separate helper methods to search only PDF or only audio collections, while handling logging and exceptions throughout the retrieval process.

"""

from typing import List, Dict, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import Filter

from src.embeddings.embedding_model import OllamaEmbeddingModel
from src.config.vectorstore_config import get_config
from src.config.retrieval_config import get_config as get_retrieval_config
from src.utils.logger import get_logger
from src.utils.exceptions import VectorStoreException

logger = get_logger(__name__)


class VectorRetriever:
    """
    Retrieves relevant chunks from Qdrant
    using dense vector similarity search.
    """

    def __init__(self):
        try:
            logger.info("Initializing VectorRetriever.")

            self.vs_config = get_config()
            self.retrieval_config = get_retrieval_config()

            self.client = QdrantClient(
                host=self.vs_config.host,
                port=self.vs_config.port,
            )

            self.embedder = OllamaEmbeddingModel()

            self.pdf_collection = self.vs_config.pdf_collection
            self.audio_collection = self.vs_config.video_collection

            logger.info("VectorRetriever initialized successfully.")

        except Exception as error:
            logger.exception("VectorRetriever initialization failed.")
            raise VectorStoreException(
                message="Failed to initialize VectorRetriever",
                details=str(error)
            ) from error

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        collection: Optional[str] = None,
        filters: Optional[Dict] = None,
    ) -> List[Dict]:
        """
        Retrieve top-k chunks from Qdrant
        for the given query.

        Args:
            query: Search query string
            top_k: Number of results to return
            collection: 'pdf', 'audio', or None (searches both)
            filters: Optional metadata filters

        Returns:
            List of result dicts with text, metadata, score
        """

        try:

            if not query or not query.strip():
                raise VectorStoreException(
                    message="Query cannot be empty"
                )

            top_k = top_k or self.retrieval_config.top_k_initial

            logger.info(
                f"Retrieving top {top_k} results "
                f"for query: '{query[:60]}'..."
            )

            # Generate query embedding
            embeddings = self.embedder.embed([query])

            if not embeddings or len(embeddings) == 0:
                logger.error(
                    f"Ollama returned empty embedding for query: '{query[:60]}'. "
                    f"Make sure Ollama is running and bge-m3 model is loaded."
                )

                raise VectorStoreException(
                    message="Embedding generation returned empty result",
                    details="Ollama may not be running or bge-m3 model not loaded. "
                            "Run: ollama pull bge-m3"
                )

            query_embedding = embeddings[0]

            if not query_embedding:
                raise VectorStoreException(
                    message="Query embedding is empty",
                    details="Ollama returned an empty vector"
                )
            results = []

            # Determine which collections to search
            collections_to_search = []

            if collection == "pdf":
                collections_to_search = [self.pdf_collection]

            elif collection == "audio":
                collections_to_search = [self.audio_collection]

            else:
                collections_to_search = [
                    self.pdf_collection,
                    self.audio_collection
                ]

            # Search each collection
            for col in collections_to_search:

                try:

                    # hits = self.client.search(
                    #     collection_name=col,
                    #     query_vector=query_embedding,
                    #     limit=top_k,
                    # )

                    hits = self._search(
                        col,
                        query_embedding,
                        top_k,
                    )

                    for hit in hits:

                        results.append({
                            "chunk_id": hit.payload.get("chunk_id"),
                            "parent_id": hit.payload.get("parent_id"),
                            "text": hit.payload.get("text"),
                            "metadata": hit.payload.get("metadata", {}),
                            "score": hit.score,
                            "collection": col,
                            "source_type": (
                                "pdf"
                                if col == self.pdf_collection
                                else "audio"
                            ),
                        })

                except Exception as col_error:

                    logger.warning(
                        f"Search failed for collection '{col}': {col_error}"
                    )

                    continue

            # Sort by score descending
            results = sorted(
                results,
                key=lambda x: x["score"],
                reverse=True
            )[:top_k]

            logger.info(
                f"Vector retrieval returned {len(results)} results."
            )

            return results

        except VectorStoreException:
            raise

        except Exception as error:

            logger.exception("Vector retrieval failed.")

            raise VectorStoreException(
                message="Vector retrieval failed",
                details=str(error)
            ) from error

    def retrieve_pdf(
        self,
        query: str,
        top_k: Optional[int] = None,
    ) -> List[Dict]:
        """Retrieve from PDF collection only."""
        return self.retrieve(query, top_k=top_k, collection="pdf")

    def retrieve_audio(
        self,
        query: str,
        top_k: Optional[int] = None,
    ) -> List[Dict]:
        """Retrieve from audio collection only."""
        return self.retrieve(query, top_k=top_k, collection="audio")

    def _search(self, collection_name: str, query_vector: list, top_k: int):
        """
        Unified search that works with both:
            - qdrant-client >= 1.7 -> uses .query_points()
            - qdrant-client < 1.7 -> uses .search()

        Always returns a list of ScoredPoint objects.
        """

        # Try new API first (>= 1.7)
        if hasattr(self.client, "query_points"):
            response = self.client.query_points(
                collection_name=collection_name,
                query=query_vector,
                limit=top_k,
                with_payload=True,
            )

            # query_points returns a QueryResponse with a .points attribute
            return response.points

        # Fallback: old API (< 1.7)
        return self.client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=top_k,
        )