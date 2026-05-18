# config/vectorstore_config.py
"""
Configuration specific to the vector store (Qdrant) module.
"""

from pydantic import BaseModel
from src.config.settings import get_settings


class VectorStoreConfig(BaseModel):
    """Configuration for Qdrant vector store"""

    # Connection settings
    host: str
    port: int
    grpc_port: int

    # Collection settings
    collection_name: str
    vector_size: int
    distance: str

    # Collections
    pdf_collection: str
    video_collection: str

    class Config:
        frozen = True


def get_vectorstore_config() -> VectorStoreConfig:
    """Create vector store config from main settings"""
    settings = get_settings()

    return VectorStoreConfig(
        host=settings.qdrant_host,
        port=settings.qdrant_port,
        grpc_port=settings.qdrant_grpc_port,
        collection_name=settings.qdrant_collection_name,
        vector_size=settings.qdrant_vector_size,
        distance=settings.qdrant_distance,
        pdf_collection=settings.qdrant_pdf_collection,
        video_collection=settings.qdrant_video_collection
    )


# Singleton
_vectorstore_config = None


def get_config() -> VectorStoreConfig:
    """Get or create vector store config singleton"""
    global _vectorstore_config

    if _vectorstore_config is None:
        _vectorstore_config = get_vectorstore_config()

    return _vectorstore_config