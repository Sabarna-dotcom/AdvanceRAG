"""
PDF ingestion pipeline.
"""

import json

from src.embeddings.pdf_batch_embedder import (
    PDFBatchEmbedder
)

from src.vectorstore.pdf_indexing import (
    PDFIndexingManager
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
# Logger
# ==========================================

logger = get_logger(__name__)

config = get_config()

import os

PDF_CHUNKS_PATH = os.path.join(

    config.paths.processed_pdf_dir,

    "chunks",

    "pdf_chunks.json"
)

def load_pdf_chunks():

    try:

        logger.info(
            "Loading PDF chunks."
        )

        with open(

            PDF_CHUNKS_PATH,

            "r",

            encoding="utf-8"

        ) as file:

            chunks = json.load(file)

        logger.info(
            f"Loaded "
            f"{len(chunks)} "
            f"PDF chunks."
        )

        return chunks

    except Exception as error:

        logger.exception(
            "Failed to load "
            "PDF chunks."
        )

        raise LLMException(

            message=(
                "Failed to load "
                "PDF chunks"
            ),

            details=str(error)

        ) from error


def main():

    try:

        logger.info(
            "Starting PDF ingestion "
            "pipeline."
        )

        pdf_chunks = (
            load_pdf_chunks()
        )

        embedder = (
            PDFBatchEmbedder()
        )

        embedded_chunks = (
            embedder.generate_embeddings(
                pdf_chunks
            )
        )

        indexer = (
            PDFIndexingManager()
        )

        indexer.index_chunks(
            embedded_chunks
        )

        logger.info(
            "PDF ingestion completed "
            "successfully."
        )

    except (
        LLMException,
        VectorStoreException
    ):

        raise

    except Exception as error:

        logger.exception(
            "PDF ingestion pipeline "
            "failed."
        )

        raise Exception(

            f"PDF ingestion failed: "
            f"{error}"

        ) from error


if __name__ == "__main__":

    main()