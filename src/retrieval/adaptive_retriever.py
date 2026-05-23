"""
Adaptive retriever - detects query complexity
and dynamically adjusts top_k for retrieval.

This `AdaptiveRetriever` code is used in your Advanced RAG system to intelligently decide how many chunks (`top_k`) should be retrieved from Qdrant based on the user query type.
It first analyzes the query intent using keywords like “compare”, “what is”, “how”, etc., then classifies the query as simple, explanation, comparison, or complex. Based on that intent, it dynamically sets retrieval depth (small `top_k` for simple queries, larger `top_k` for complex queries) and finally calls the `HybridRetriever` to fetch the most relevant chunks from PDF/audio collections.
This improves both retrieval quality and efficiency in the RAG pipeline.

"""

from typing import List, Dict, Optional

from src.retrieval.hybrid_retriever import HybridRetriever
from src.config.retrieval_config import get_config as get_retrieval_config
from src.utils.logger import get_logger
from src.utils.exceptions import VectorStoreException


logger = get_logger(__name__)


# Query intent -> top_k mapping
INTENT_TOP_K = {
    "simple_fact": 5,
    "definition": 5,
    "explanation": 10,
    "comparison": 15,
    "complex_multi_part": 25,
    "default": 10
}


# Keywords that hint at each intent type
INTENT_KEYWORDS = {
    "comparison": [
        "compare",
        "difference",
        "vs",
        "versus",
        "contrast",
        "better",
        "worse"
    ],

    "complex_multi_part": [
        "how does",
        "explain in detail",
        "what are all",
        "describe the process",
        "relationship between"
    ],

    "definition": [
        "what is",
        "define",
        "meaning of",
        "what are"
    ],

    "explanation": [
        "how",
        "why",
        "explain",
        "describe"
    ],

    "simple_fact": [
        "who",
        "when",
        "where",
        "which"
    ]
}


class AdaptiveRetriever:
    """
    Dynamically determines retrieval depth (top_k)
    based on the complexity/intent of the query
    then runs hybrid retrieval with appropriate settings.
    """

    def __init__(self):

        try:

            logger.info("Initializing AdaptiveRetriever")

            self.hybrid_retriever = HybridRetriever()

            self.retrieval_config = get_retrieval_config()

            logger.info("AdaptiveRetriever initialized successfully")

        except Exception as error:

            logger.exception("AdaptiveRetriever initialization failed")

            raise VectorStoreException(
                message="Failed to initialize AdaptiveRetriever",
                details=str(error)
            ) from error

    def detect_intent(self, query: str) -> str:
        """
        Detect query intent from keywords.

        Returns one of:

            simple_fact | definition | explanation
            comparison | complex_multi_part | default
        """

        query_lower = query.lower()

        for intent, keywords in INTENT_KEYWORDS.items():

            if any(kw in query_lower for kw in keywords):

                logger.info(f"Detected query intent: {intent}")

                return intent

        return "default"

    def determine_top_k(self, query: str) -> int:
        """
        Determine top_k based on query intent.
        """

        intent = self.detect_intent(query)

        top_k = INTENT_TOP_K.get(
            intent,
            INTENT_TOP_K["default"]
        )

        logger.info(
            f"Adaptive top_k = {top_k} (intent: {intent})"
        )

        return top_k

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        collection: Optional[str] = None,
    ) -> List[Dict]:
        """
        Adaptive retrieval - auto-selects top_k
        based on query complexity.

        Args:

            query:
                User query

            top_k:
                Override top_k (optional)

            collection:
                'pdf', 'audio', or None

        Returns:

            Retrieved chunks
        """

        try:

            if not query or not query.strip():

                raise VectorStoreException(
                    message="Query cannot be empty"
                )

            # Auto-determine top_k if not provided
            if top_k is None:

                top_k = self.determine_top_k(query)

            logger.info(
                f"Adaptive retrieval: query='{query[:60]}' "
                f"top_k={top_k}"
            )

            results = self.hybrid_retriever.retrieve(
                query=query,
                top_k=top_k,
                collection=collection,
            )

            # Tag with intent info
            intent = self.detect_intent(query)

            for result in results:

                result["query_intent"] = intent

            logger.info(
                f"Adaptive retrieval returned "
                f"{len(results)} results."
            )

            return results

        except VectorStoreException:
            raise

        except Exception as error:

            logger.exception("Adaptive retrieval failed")

            raise VectorStoreException(
                message="Adaptive retrieval failed",
                details=str(error)
            ) from error