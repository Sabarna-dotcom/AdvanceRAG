"""
Local embedding model using Ollama.
"""

from typing import List,Union
import ollama
from src.config.embedding_config import get_config
from src.utils.logger import get_logger
from src.utils.exceptions import LLMException

# ==========================================
# Logger
# ==========================================

logger = get_logger(__name__)


class OllamaEmbeddingModel:
    """
    Wrapper for Ollama embedding models.
    """

    def __init__(self):
        """
        Initialize embedding model.
        """

        try:

            logger.info("Initializing embedding model...")
            self.config = get_config()

            # Model name
            self.model_name = self.config.model_name

            # Ollama client
            self.client = ollama.Client(
                host=(
                    self.config.ollama_base_url
                )
            )

            logger.info(
                f"Embedding model initialized "
                f"successfully | "
                f"Model: {self.model_name}"
            )

        except Exception as error:

            logger.exception(
                "Failed to initialize "
                "embedding model."
            )

            raise LLMException(

                message=(
                    "Embedding model "
                    "initialization failed"
                ),

                details=str(error)

            ) from error

    def embed(
        self,
        texts: Union[str, List[str]]
    ) -> List[List[float]]:
        """
        Generate embeddings for text(s).

        Args:
            texts:
                Single string or list
                of strings

        Returns:
            List of embedding vectors
        """

        try:

            # Empty validation
            if not texts:

                logger.warning(
                    "Empty input received "
                    "for embedding."
                )

                raise LLMException(
                    message=(
                        "Input texts cannot "
                        "be empty"
                    )
                )

            # Single text → list
            if isinstance(texts, str):

                logger.info(
                    "Single text received. "
                    "Converting to list."
                )

                texts = [texts]

            all_embeddings = []

            logger.info(
                f"Starting embedding "
                f"generation for "
                f"{len(texts)} texts."
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
                "Embedding generation "
                "completed successfully."
            )

            return all_embeddings

        except LLMException:

            raise

        except Exception as error:

            logger.exception("Embedding generation failed.")

            raise LLMException(

                message=(
                    "Failed to generate "
                    "embeddings"
                ),

                details=str(error)

            ) from error

    def _embed_batch(
            self,
            batch: List[str]
    ) -> List[List[float]]:
        """
        Generate embeddings
        for a batch.
        """

        embeddings = []

        try:

            for index, text in enumerate(batch):

                try:

                    # ==========================
                    # Empty Validation
                    # ==========================

                    if not text:
                        logger.warning(
                            f"Empty text chunk "
                            f"skipped at "
                            f"index {index}"
                        )

                        continue

                    text = str(text).strip()

                    if not text:
                        logger.warning(
                            f"Blank text chunk "
                            f"skipped at "
                            f"index {index}"
                        )

                        continue

                    # ==========================
                    # Debug Logging
                    # ==========================

                    logger.info(
                        f"Generating embedding "
                        f"for chunk {index + 1} "
                        f"| Length: {len(text)}"
                    )

                    # ==========================
                    # Generate Embedding
                    # ==========================

                    response = (
                        self.client.embeddings(

                            model=self.model_name,

                            prompt=text
                        )
                    )

                    embedding = response.get(
                        "embedding"
                    )

                    # ==========================
                    # Validate Embedding
                    # ==========================

                    if not embedding:
                        logger.warning(
                            f"Empty embedding "
                            f"received for "
                            f"chunk {index + 1}"
                        )

                        continue

                    embeddings.append(
                        embedding
                    )

                except Exception as chunk_error:

                    logger.warning(
                        f"Skipping problematic "
                        f"chunk {index + 1} "
                        f"| Error: "
                        f"{chunk_error}"
                    )

                    continue

            logger.info(
                f"Batch embedding generation "
                f"successful | "
                f"Generated "
                f"{len(embeddings)} embeddings."
            )

            return embeddings

        except Exception as error:

            logger.exception(
                "Batch embedding generation "
                "failed."
            )

            raise LLMException(

                message=(
                    "Failed to generate "
                    "batch embeddings"
                ),

                details=str(error)

            ) from error

    def get_dimension(self) -> int:
        """
        Get embedding dimension.
        """

        try:

            logger.info(
                "Fetching embedding "
                "dimension."
            )

            return self.config.dimension

        except Exception as error:

            logger.exception(
                "Failed to fetch "
                "embedding dimension."
            )

            raise LLMException(

                message=(
                    "Could not get "
                    "embedding dimension"
                ),

                details=str(error)

            ) from error

    def get_model_name(self) -> str:
        """
        Get model name.
        """

        try:

            logger.info(
                "Fetching embedding "
                "model name."
            )

            return self.model_name

        except Exception as error:

            logger.exception(
                "Failed to fetch "
                "model name."
            )

            raise LLMException(

                message=(
                    "Could not get "
                    "model name"
                ),

                details=str(error)

            ) from error


# ==========================================
# Example Usage
# ==========================================

if __name__ == "__main__":

    try:

        # Initialize embedder
        embedder = (
            OllamaEmbeddingModel()
        )

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

            "Photosynthesis converts "
            "light into energy",

            "The Calvin cycle is "
            "part of photosynthesis"
        ])

        print(
            f"Generated "
            f"{len(embeddings)} embeddings"
        )

        print(
            f"Each embedding has "
            f"{len(embeddings[0])} "
            f"dimensions"
        )

    except LLMException as error:

        logger.error(
            f"Application failed: {error}"
        )

        print(
            f"Error: {error}"
        )