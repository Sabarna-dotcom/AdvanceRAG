"""
RAG Fusion Retriever - generates multiple query variations
using LLM, retrieves for each, then merges using RRF.

Fusion Retrieval in the RAG system improves retrieval accuracy by generating multiple variations of the user query using an LLM, retrieving relevant chunks separately for each variation from the vector database,
and then combining all retrieved results using Reciprocal Rank Fusion (RRF). This approach helps the system capture different semantic meanings and phrasings of the same question,
ensuring that important context is not missed due to wording differences and ultimately providing more relevant and high-quality information for final answer generation.


RRF (Reciprocal Rank Fusion) is a ranking algorithm used to combine results from multiple retrieval searches into one final ranked list.
In Fusion Retrieval, each query variation retrieves its own ranked chunks, and RRF assigns scores based on chunk positions in those lists using the formula: RRF\ Score = \sum \frac{1}{k + rank} where `rank` is the position of a chunk in a retrieval list and `k` is a constant (commonly 60).
Chunks appearing repeatedly across multiple query variations receive higher combined scores, making them rank higher in the final results. This improves retrieval robustness and relevance.


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


class FusionRetriever:
    """
    RAG Fusion Retriever.

    1. Generates N variations of the original query using LLM
    2. Retrieves for each variation
    3. Merges all results using Reciprocal Rank Fusion (RRF)
    """

    def __init__(self):

        try:

            logger.info("Initializing FusionRetriever")

            self.llm = OllamaLLM()

            self.vector_retriever = VectorRetriever()

            self.retrieval_config = get_retrieval_config()

            self.num_queries = (
                self.retrieval_config.fusion_num_queries
            )

            logger.info(
                "FusionRetriever initialized successfully"
            )

        except Exception as error:

            logger.exception(
                "FusionRetriever initialization failed."
            )

            raise LLMException(
                message="Failed to initialize FusionRetriever",
                details=str(error)
            ) from error

    def generate_query_variations(
        self,
        query: str
    ) -> List[str]:
        """
        Generate N variations of the query using LLM.
        """

        prompt = f"""
Generate {self.num_queries} different ways to ask the following question.

Each variation should be on its own line starting with a dash (-).
Keep the same meaning but use different words or perspectives.
Only return the variations, nothing else.

Original question: {query}

Variations:
"""

        try:

            response = self.llm.generate(prompt)

            variations = self.parse_variations(response)

            logger.info(
                f"Generated {len(variations)} query variations."
            )

            return variations

        except Exception as error:

            logger.warning(
                f"Query variation generation failed: {error}"
            )

            return [query]

    def parse_variations(
        self,
        response: str
    ) -> List[str]:
        """
        Parse LLM response into a list of query variations.
        """

        lines = response.strip().split("\n")

        variations = []

        for line in lines:

            line = line.strip()

            for prefix in ["-", "*"]:

                if line.startswith(prefix):

                    line = line[len(prefix):].strip()

            if len(line) > 2 and line[0].isdigit() and line[1] in [".", ")"]:

                line = line[2:].strip()

            if line and len(line) > 5:

                variations.append(line)

        return variations

    def reciprocal_rank_fusion(
        self,
        result_lists: List[List[Dict]],
        k: int = 60
    ) -> List[Dict]:
        """
        Merge multiple result lists using RRF.
        """

        scores = {}

        chunk_map = {}

        for result_list in result_lists:

            for rank, result in enumerate(result_list, start=1):

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

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        collection: Optional[str] = None,
    ) -> List[Dict]:
        """
        RAG Fusion retrieval:

        1. Generate query variations
        2. Retrieve for each variation
        3. Fuse with RRF

        Args:

            query:
                Original query

            top_k:
                Final number of results

            collection:
                'pdf', 'audio', or None

        Returns:

            Fused and ranked results
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
                f"Fusion retrieval for: {query[:60]}"
            )

            # Generate variations (always include original)
            variations = self.generate_query_variations(query)

            if query not in variations:

                variations.insert(0, query)

            # Retrieve for each variation
            all_result_lists = []

            for variation in variations:

                try:

                    results = self.vector_retriever.retrieve(
                        query=variation,
                        top_k=top_k,
                        collection=collection,
                    )

                    if results:

                        all_result_lists.append(results)

                except Exception as var_error:

                    logger.warning(
                        f"Retrieval failed for variation "
                        f"'{variation[:40]}': {var_error}"
                    )

                    continue

            if not all_result_lists:

                logger.warning(
                    "No results from any query variation."
                )

                return []

            # Fuse with RRF
            fused = self.reciprocal_rank_fusion(
                all_result_lists
            )

            final = fused[:top_k]

            # Tag results
            for result in final:

                result["retrieval_method"] = "fusion"

            logger.info(
                f"Fusion retrieval returned "
                f"{len(final)} results."
            )

            return final

        except (VectorStoreException, LLMException):

            raise

        except Exception as error:

            logger.exception("Fusion retrieval failed.")

            raise VectorStoreException(
                message="Fusion retrieval failed",
                details=str(error)
            ) from error