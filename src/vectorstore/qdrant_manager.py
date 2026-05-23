"""
Qdrant vector database manager.
"""

from typing import List, Dict

from qdrant_client import QdrantClient

from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
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

    def __init__(
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
    ):

        try:

            logger.info(
                f"Uploading {len(chunks)} "
                f"chunks to "
                f"{self.collection_name}"
            )

            points = []

            for idx, chunk in enumerate(chunks):
                point = PointStruct(

                    id=idx,

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