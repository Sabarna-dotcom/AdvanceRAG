"""
Audio transcript indexing pipeline.
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

# ==========================================
# Logger
# ==========================================

logger = get_logger(__name__)


class AudioIndexingManager:
    """
    Handles audio transcript indexing.
    """

    def _init_(self):

        try:

            logger.info(
                "Initializing audio "
                "indexing manager."
            )

            self.vector_db = (
                QdrantManager(
                    collection_name=(
                        "audio_collection"
                    )
                )
            )

        except Exception as error:

            logger.exception(
                "Audio indexing manager "
                "initialization failed."
            )

            raise VectorStoreException(

                message=(
                    "Failed to initialize "
                    "audio indexing manager"
                ),

                details=str(error)

            ) from error

    def index_chunks(
        self,
        chunks: List[Dict]
    ) -> List[str]:
        """
        Upload transcript embeddings into Qdrant.
        Returns list of UUID point IDs assigned.
        """

        try:

            if not chunks:

                raise VectorStoreException(

                    message=(
                        "Audio chunks "
                        "cannot be empty"
                    )
                )

            logger.info(
                f"Uploading "
                f"{len(chunks)} "
                f"audio transcript chunks."
            )

            point_ids = self.vector_db.upload_chunks(
                chunks
            )

            logger.info(
                "Audio transcript indexing "
                "completed."
            )

            return point_ids

        except VectorStoreException:

            raise

        except Exception as error:

            logger.exception(
                "Audio indexing failed."
            )

            raise VectorStoreException(

                message=(
                    "Failed to index "
                    "audio transcript chunks"
                ),

                details=str(error)

            ) from error