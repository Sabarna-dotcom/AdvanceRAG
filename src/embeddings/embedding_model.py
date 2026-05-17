# src/embeddings/embedding_model.py

"""
Local embedding model using Ollama.
"""

import logging
from typing import List, Union

import ollama

from src.embeddings.config.embedding_config import get_config


# ==========================================
# Logger Configuration
# ==========================================

logging.basicConfig(
    filename="logs/embedding.log",
    level=logging.INFO,
    format=(
        "%(asctime)s - "
        "%(name)s - "
        "%(levelname)s - "
        "%(message)s"
    )
)

logger = logging.getLogger(__name__)


class OllamaEmbeddingModel:
    """
    Wrapper for Ollama embedding models.
    """

    def __init__(self):
        """Initialize embedding model configuration"""

        try:

            self.config = get_config()

            # Model name from config
            self.model_name = (
                self.config.model_name
            )

            # Ollama client
            self.client = ollama.Client(
                host=self.config.ollama_base_url
            )

            logger.info(
                f"Ollama embedding model "
                f"initialized successfully: "
                f"{self.model_name}"
            )

        except Exception as e:

            logger.error(
                f"Failed to initialize "
                f"embedding model: {e}"
            )

            raise Exception(
                "Embedding model initialization "
                "failed"
            ) from e

    def embed(
        self,
        texts: Union[str, List[str]]
    ) -> List[List[float]]:
        """
        Generate embeddings for text(s).

        Args:
            texts: Single string or list of strings

        Returns:
            List of embedding vectors
        """

        try:

            # Convert single string → list
            if isinstance(texts, str):

                logger.info(
                    "Single text received. "
                    "Converting to list."
                )

                texts = [texts]

            all_embeddings = []

            logger.info(
                f"Starting embedding generation "
                f"for {len(texts)} texts"
            )

            # Batch processing
            for i in range(
                0,
                len(texts),
                self.config.batch_size
            ):

                batch = texts[
                    i:i + self.config.batch_size
                ]

                logger.info(
                    f"Processing batch "
                    f"{i // self.config.batch_size + 1}"
                )

                batch_embeddings = (
                    self._embed_batch(batch)
                )

                all_embeddings.extend(
                    batch_embeddings
                )

            logger.info(
                "Embedding generation completed "
                "successfully"
            )

            return all_embeddings

        except Exception as e:

            logger.error(
                f"Embedding generation failed: {e}"
            )

            raise Exception(
                "Failed to generate embeddings"
            ) from e

    def _embed_batch(
        self,
        batch: List[str]
    ) -> List[List[float]]:
        """
        Generate embeddings for a batch.
        """

        embeddings = []

        try:

            for text in batch:

                logger.info(
                    "Generating embedding "
                    "for text chunk"
                )

                response = (
                    self.client.embeddings(
                        model=self.model_name,
                        prompt=text
                    )
                )

                embeddings.append(
                    response["embedding"]
                )

            logger.info(
                "Batch embedding generation "
                "successful"
            )

            return embeddings

        except Exception as e:

            logger.error(
                f"Batch embedding generation "
                f"failed: {e}"
            )

            raise Exception(
                "Failed to generate batch "
                "embeddings"
            ) from e

    def get_dimension(self) -> int:
        """Get embedding dimension"""

        try:

            logger.info(
                "Fetching embedding dimension"
            )

            return self.config.dimension

        except Exception as e:

            logger.error(
                f"Failed to fetch dimension: {e}"
            )

            raise Exception(
                "Could not get embedding "
                "dimension"
            ) from e

    def get_model_name(self) -> str:
        """Get model name"""

        try:

            logger.info(
                "Fetching model name"
            )

            return self.model_name

        except Exception as e:

            logger.error(
                f"Failed to fetch model "
                f"name: {e}"
            )

            raise Exception(
                "Could not get model name"
            ) from e


# ==========================================
# Example Usage
# ==========================================

if __name__ == "__main__":

    # Initialize embedder
    embedder = OllamaEmbeddingModel()

    # Single text
    embedding = embedder.embed(
        "This is a test"
    )

    print(
        f"Single embedding dimension: "
        f"{len(embedding[0])}"
    )

    # Multiple texts
    embeddings = embedder.embed([
        "Photosynthesis converts light into energy",
        "The Calvin cycle is part of photosynthesis"
    ])

    print(
        f"Generated {len(embeddings)} embeddings"
    )

    print(
        f"Each embedding has "
        f"{len(embeddings[0])} dimensions"
    )