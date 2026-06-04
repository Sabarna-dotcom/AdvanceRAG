"""
Qdrant vector database manager.
"""

import uuid
from typing import List, Dict

from qdrant_client import QdrantClient

from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    PointIdsList,
    Filter,
    FieldCondition,
    MatchValue,
)

from src.config.vectorstore_config import (
    get_config
)

from src.utils.logger import (
    get_logger
)

from src.utils.exceptions import (
    VectorStoreException
)

from src.embeddings.embedding_model import (
    OllamaEmbeddingModel
)


logger = get_logger(__name__)


class QdrantManager:

    def _init_(
        self,
        collection_name: str
    ):

        try:

            self.config = get_config()

            self.collection_name = (
                collection_name
            )

            self.client = QdrantClient(

                host=self.config.host,

                port=self.config.port,
            )

            self.embedding_dimension = (
                OllamaEmbeddingModel()
                .get_dimension()
            )

            self.create_collection()

        except Exception as error:

            logger.exception(
                "Failed to initialize Qdrant."
            )

            raise VectorStoreException(

                message=(
                    "Qdrant initialization failed"
                ),

                details=str(error)

            ) from error

    def create_collection(self):

        try:

            collections = (
                self.client.get_collections()
            )

            existing_collections = [

                collection.name

                for collection
                in collections.collections
            ]

            if (
                self.collection_name
                not in existing_collections
            ):

                logger.info(
                    f"Creating collection: "
                    f"{self.collection_name}"
                )

                self.client.create_collection(

                    collection_name=(
                        self.collection_name
                    ),

                    vectors_config=VectorParams(

                        size=(
                            self.embedding_dimension
                        ),

                        distance=Distance.COSINE,
                    ),
                )

        except Exception as error:

            logger.exception(
                "Collection creation failed."
            )

            raise VectorStoreException(

                message=(
                    "Failed to create collection"
                ),

                details=str(error)

            ) from error

    def upload_chunks(
            self,
            chunks: List[Dict]
    ) -> List[str]:
        """Upload chunks to Qdrant. Returns list of UUID strings assigned to each point."""

        try:

            logger.info(
                f"Uploading {len(chunks)} "
                f"chunks to "
                f"{self.collection_name}"
            )

            points     = []
            point_ids  = []

            for chunk in chunks:
                point_id = str(uuid.uuid4())
                point_ids.append(point_id)

                point = PointStruct(

                    id=point_id,

                    vector=chunk["embedding"],

                    payload={

                        "chunk_id": chunk.get(
                            "chunk_id"
                        ),

                        "parent_id": chunk.get(
                            "parent_id"
                        ),

                        "text": chunk.get(
                            "text"
                        ),

                        "metadata": chunk.get(
                            "metadata"
                        ),
                    }
                )

                points.append(point)

            # ==================================
            # Batched Upload
            # ==================================

            batch_size = 100

            total_batches = (

                                    len(points) + batch_size - 1

                            ) // batch_size

            for i in range(

                    0,
                    len(points),
                    batch_size
            ):
                batch_points = points[
                    i:i + batch_size
                ]

                current_batch = (
                                        i // batch_size
                                ) + 1

                logger.info(
                    f"Uploading batch "
                    f"{current_batch}/"
                    f"{total_batches}"
                )

                self.client.upsert(

                    collection_name=(
                        self.collection_name
                    ),

                    points=batch_points,
                )

            logger.info(
                "Chunk upload successful."
            )

            return point_ids

        except Exception as error:

            logger.exception(
                "Chunk upload failed."
            )

            raise VectorStoreException(

                message=(
                    "Failed to upload chunks"
                ),

                details=str(error)

            ) from error

    def delete_by_ids(self, point_ids: List[str]):
        """Delete specific points by their Qdrant point IDs."""
        if not point_ids:
            return
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=PointIdsList(points=point_ids),
            )
            logger.info(
                f"Deleted {len(point_ids)} points from {self.collection_name}."
            )
        except Exception as error:
            logger.exception("delete_by_ids failed.")
            raise VectorStoreException(
                message="Failed to delete points by IDs",
                details=str(error),
            ) from error

    def delete_by_source(self, source_filename: str):
        """
        Delete ALL points whose metadata.source matches source_filename.
        Used as a fallback when exact point IDs are not tracked.
        """
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="metadata.source",
                            match=MatchValue(value=source_filename),
                        )
                    ]
                ),
            )
            logger.info(
                f"Deleted points for source='{source_filename}' "
                f"from {self.collection_name}."
            )
        except Exception as error:
            logger.exception("delete_by_source failed.")
            raise VectorStoreException(
                message="Failed to delete points by source",
                details=str(error),
            ) from error
 