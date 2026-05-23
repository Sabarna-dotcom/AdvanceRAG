"""
Audio embedding + indexing pipeline.
"""

import os
import json

from src.embeddings.audio_batch_embedder import (
    AudioBatchEmbedder
)

from src.vectorstore.audio_indexing import (
    AudioIndexingManager
)

from src.utils.logger import (
    get_logger
)

from src.config.ingestion_config import (
    get_config
)

from src.utils.exceptions import (
    LLMException,
    VectorStoreException
)

# ==========================================
# Logger & Config
# ==========================================

logger = get_logger(__name__)

config = get_config()

TRANSCRIPT_DIRECTORY = (
    config.paths.processed_transcript_dir
)


def load_transcript_chunks():
    """
    Load all transcript chunks
    from transcript JSON files.
    """

    try:

        all_chunks = []

        logger.info(
            "Loading transcript JSON files."
        )

        for file_name in os.listdir(
            TRANSCRIPT_DIRECTORY
        ):

            if file_name.endswith(".json"):

                file_path = os.path.join(
                    TRANSCRIPT_DIRECTORY,
                    file_name
                )

                logger.info(
                    f"Loading transcript: "
                    f"{file_name}"
                )

                with open(
                    file_path,
                    "r",
                    encoding="utf-8"
                ) as file:

                    data = json.load(file)

                transcript_chunks = (
                    data.get("chunks", [])
                )

                all_chunks.extend(
                    transcript_chunks
                )

        logger.info(
            f"Loaded "
            f"{len(all_chunks)} "
            f"transcript chunks."
        )

        return all_chunks

    except Exception as error:

        logger.exception(
            "Failed to load transcript "
            "chunks."
        )

        raise LLMException(

            message=(
                "Failed to load "
                "audio transcript chunks"
            ),

            details=str(error)

        ) from error


def main():

    try:

        logger.info(
            "Starting audio ingestion."
        )

        transcript_chunks = (
            load_transcript_chunks()
        )

        embedder = (
            AudioBatchEmbedder()
        )

        embedded_chunks = (
            embedder.generate_embeddings(
                transcript_chunks
            )
        )

        indexer = (
            AudioIndexingManager()
        )

        indexer.index_chunks(
            embedded_chunks
        )

        logger.info(
            "Audio ingestion completed."
        )

    except (
        LLMException,
        VectorStoreException
    ):

        raise

    except Exception as error:

        logger.exception(
            "Audio ingestion pipeline failed."
        )

        raise Exception(

            f"Audio ingestion failed: "
            f"{error}"

        ) from error


if __name__ == "__main__":

    main()