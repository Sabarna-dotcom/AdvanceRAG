# src/embeddings/config/embedding_config.py

"""
Configuration specific to the embeddings module.
Only includes settings relevant to embedding generation.
"""

from pydantic import BaseModel
from src.config.settings import get_settings


class EmbeddingConfig(BaseModel):
    """Configuration for embedding generation"""

    # Ollama model settings
    model_name: str
    dimension: int

    # Processing settings
    batch_size: int
    max_retries: int
    timeout: int

    # Ollama settings
    ollama_base_url: str

    class Config:
        frozen = True  # Make immutable


def get_embedding_config() -> EmbeddingConfig:
    """
    Create embedding config from main settings.
    Only extracts embedding-relevant settings.
    """

    settings = get_settings()

    return EmbeddingConfig(

        # Model settings
        model_name=settings.embedding_model,
        dimension=settings.embedding_dimension,

        # Processing settings
        batch_size=settings.embedding_batch_size,
        max_retries=settings.embedding_max_retries,
        timeout=settings.embedding_timeout,

        # Ollama settings
        ollama_base_url=settings.ollama_base_url
    )


# ==========================================
# Singleton instance for embeddings
# ==========================================

_embedding_config = None


def get_config() -> EmbeddingConfig:
    """Get or create embedding config singleton"""

    global _embedding_config

    if _embedding_config is None:
        _embedding_config = get_embedding_config()

    return _embedding_config