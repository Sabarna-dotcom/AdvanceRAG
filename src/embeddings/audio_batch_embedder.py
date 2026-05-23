"""
Audio transcript embedding pipeline.
"""

import math

from typing import (
    List,
    Dict
)

from src.embeddings.embedding_model import (
    OllamaEmbeddingModel
)

from src.utils.logger import (
    get_logger
)

from src.utils.exceptions import (
    LLMException
)

# ==========================================
# Logger
# ==========================================

logger = get_logger(__name__)


class AudioBatchEmbedder:
    """
    Embed transcript JSON chunks.
    """

    def __init__(self):

        try:

            logger.info(
                "Initializing audio "
                "batch embedder."
            )

            self.embedding_model = (
                OllamaEmbeddingModel()
            )

        except Exception as error:

            logger.exception(
                "Audio embedder "
                "initialization failed."
            )

            raise LLMException(

                message=(
                    "Failed to initialize "
                    "audio embedder"
                ),

                details=str(error)

            ) from error

    def generate_embeddings(
        self,
        transcript_chunks: List[Dict]
    ) -> List[Dict]:
        """
        Generate embeddings for
        transcript JSON chunks.
        """

        try:

            if not transcript_chunks:

                raise LLMException(

                    message=(
                        "Transcript chunks "
                        "cannot be empty"
                    )
                )

            logger.info(
                f"Generating embeddings "
                f"for "
                f"{len(transcript_chunks)} "
                f"audio transcript chunks."
            )

            texts = []

            clean_chunks = []

            for chunk in transcript_chunks:

                try:

                    # =========================
                    # Text Cleaning
                    # =========================

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

                    # =========================
                    # Timestamp Cleaning
                    # =========================

                    start = chunk.get(
                        "start",
                        0
                    )

                    end = chunk.get(
                        "end",
                        0
                    )

                    if (
                        isinstance(start, float)
                        and math.isnan(start)
                    ):
                        start = 0

                    if (
                        isinstance(end, float)
                        and math.isnan(end)
                    ):
                        end = 0

                    # =========================
                    # Clean Chunk
                    # =========================

                    cleaned_chunk = {

                        "text": text,

                        "title": str(
                            chunk.get(
                                "title",
                                ""
                            )
                        ),

                        "start": start,

                        "end": end,

                        "number": str(
                            chunk.get(
                                "number",
                                ""
                            )
                        )
                    }

                    texts.append(text)

                    clean_chunks.append(
                        cleaned_chunk
                    )

                except Exception as chunk_error:

                    logger.warning(
                        f"Skipping malformed "
                        f"chunk: {chunk_error}"
                    )

                    continue

            # Replace original chunks
            transcript_chunks = clean_chunks

            logger.info(
                f"Valid transcript chunks: "
                f"{len(transcript_chunks)}"
            )

            if not transcript_chunks:

                raise LLMException(

                    message=(
                        "No valid transcript "
                        "chunks found"
                    )
                )

            # =========================
            # Generate Embeddings
            # =========================

            embeddings = (
                self.embedding_model.embed(
                    texts
                )
            )

            embedded_chunks = []

            for chunk, embedding in zip(

                transcript_chunks,
                embeddings
            ):

                embedded_chunk = {

                    "text": chunk["text"],

                    "embedding": embedding,

                    "metadata": {

                        "title": chunk[
                            "title"
                        ],

                        "start": chunk[
                            "start"
                        ],

                        "end": chunk[
                            "end"
                        ],

                        "number": chunk[
                            "number"
                        ],

                        "source_type": "audio"
                    }
                }

                embedded_chunks.append(
                    embedded_chunk
                )

            logger.info(
                "Audio embedding "
                "generation completed."
            )

            return embedded_chunks

        except LLMException:

            raise

        except Exception as error:

            logger.exception(
                "Audio embedding generation "
                "failed."
            )

            raise LLMException(

                message=(
                    "Failed to generate "
                    "audio embeddings"
                ),

                details=str(error)

            ) from error