"""
PDF indexing pipeline.
"""

from typing import (
    List,
    Dict
)

from src.vectorstore.qdrant_manager import (
    QdrantManager
)

from src.utils.logger import (
    get_logger
)

from src.utils.exceptions import (
    VectorStoreException
)


logger = get_logger(__name__)


class PDFIndexingManager:

    def __init__(self):

        try:

            logger.info(
                "Initializing PDF "
                "indexing manager."
            )

            self.vector_db = (
                QdrantManager(
                    collection_name=(
                        "pdf_collection"
                    )
                )
            )

        except Exception as error:

            logger.exception(
                "PDF indexing manager "
                "initialization failed."
            )

            raise VectorStoreException(

                message=(
                    "Failed to initialize "
                    "PDF indexing manager"
                ),

                details=str(error)

            ) from error

    def index_chunks(
        self,
        chunks: List[Dict]
    ):

        try:

            if not chunks:

                raise VectorStoreException(

                    message=(
                        "PDF chunks "
                        "cannot be empty"
                    )
                )

            logger.info(
                f"Uploading "
                f"{len(chunks)} "
                f"PDF chunks."
            )

            self.vector_db.upload_chunks(
                chunks
            )

            logger.info(
                "PDF indexing completed."
            )

        except VectorStoreException:

            raise

        except Exception as error:

            logger.exception(
                "PDF indexing failed."
            )

            raise VectorStoreException(

                message=(
                    "Failed to index "
                    "PDF chunks"
                ),

                details=str(error)

            ) from error