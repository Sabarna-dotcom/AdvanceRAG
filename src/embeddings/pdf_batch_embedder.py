"""
PDF embedding pipeline.
"""

from typing import List, Dict

from src.embeddings.embedding_model import (
    OllamaEmbeddingModel
)

from src.utils.logger import (
    get_logger
)

from src.utils.exceptions import (
    LLMException
)


logger = get_logger(__name__)


class PDFBatchEmbedder:

    def __init__(self):

        try:

            logger.info(
                "Initializing PDF "
                "batch embedder."
            )

            self.embedding_model = (
                OllamaEmbeddingModel()
            )

        except Exception as error:

            logger.exception(
                "PDF embedder initialization "
                "failed."
            )

            raise LLMException(

                message=(
                    "Failed to initialize "
                    "PDF embedder"
                ),

                details=str(error)

            ) from error

    def generate_embeddings(
        self,
        chunks: List[Dict]
    ) -> List[Dict]:

        try:

            if not chunks:

                raise LLMException(

                    message=(
                        "PDF chunks cannot "
                        "be empty"
                    )
                )

            logger.info(
                f"Generating embeddings "
                f"for "
                f"{len(chunks)} PDF chunks."
            )

            texts = []

            clean_chunks = []

            for chunk in chunks:

                try:

                    text = chunk.get(
                        "text",
                        ""
                    )

                    if text is None:
                        continue

                    text = str(text).strip()

                    if not text:
                        continue

                    if text.lower() == "nan":
                        continue

                    texts.append(text)

                    clean_chunks.append(
                        chunk
                    )

                except Exception as chunk_error:

                    logger.warning(
                        f"Skipping malformed "
                        f"PDF chunk: "
                        f"{chunk_error}"
                    )

                    continue

            logger.info(
                f"Valid PDF chunks: "
                f"{len(clean_chunks)}"
            )

            embeddings = (
                self.embedding_model.embed(
                    texts
                )
            )

            embedded_chunks = []

            for chunk, embedding in zip(

                clean_chunks,
                embeddings
            ):

                embedded_chunk = {

                    "chunk_id": chunk.get(
                        "chunk_id"
                    ),

                    "parent_id": chunk.get(
                        "parent_id"
                    ),

                    "text": chunk.get(
                        "text"
                    ),

                    "embedding": embedding,

                    "metadata": chunk.get(
                        "metadata",
                        {}
                    )
                }

                embedded_chunks.append(
                    embedded_chunk
                )

            logger.info(
                "PDF embedding generation "
                "completed."
            )

            return embedded_chunks

        except LLMException:

            raise

        except Exception as error:

            logger.exception(
                "PDF embedding generation "
                "failed."
            )

            raise LLMException(

                message=(
                    "Failed to generate "
                    "PDF embeddings"
                ),

                details=str(error)

            ) from error