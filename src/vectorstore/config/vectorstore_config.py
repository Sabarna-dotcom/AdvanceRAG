# config/vectorstore_config.py
"""
Configuration specific to the vector store (Pinecone) module.
"""

from pydantic import BaseModel
from src.config.settings import get_settings


class VectorStoreConfig(BaseModel):
    """Configuration for Pinecone vector store"""

    # API credentials
    api_key: str
    environment: str

    # Index settings
    index_name: str
    dimension: int
    metric: str

    # Namespaces
    namespace_pdf: str
    namespace_video: str

    class Config:
        frozen = True


def get_vectorstore_config() -> VectorStoreConfig:
    """Create vector store config from main settings"""
    settings = get_settings()

    return VectorStoreConfig(
        api_key=settings.pinecone_api_key,
        environment=settings.pinecone_environment,
        index_name=settings.pinecone_index_name,
        dimension=settings.pinecone_dimension,
        metric=settings.pinecone_metric,
        namespace_pdf=settings.pinecone_namespace_pdf,
        namespace_video=settings.pinecone_namespace_video
    )


# Singleton
_vectorstore_config = None


def get_config() -> VectorStoreConfig:
    """Get or create vector store config singleton"""
    global _vectorstore_config
    if _vectorstore_config is None:
        _vectorstore_config = get_vectorstore_config()
    return _vectorstore_config