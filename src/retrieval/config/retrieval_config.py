# config/retrieval_config.py
"""
Configuration specific to the retrieval module.
"""

from pydantic import BaseModel
from typing import Dict
from config.settings import get_settings


class RetrievalConfig(BaseModel):
    """Configuration for retrieval strategies"""

    # Basic retrieval
    top_k_initial: int
    top_k_final: int
    confidence_threshold: float

    # Hybrid search weights
    vector_weight: float
    keyword_weight: float

    # Advanced strategies (enabled/disabled)
    use_hyde: bool
    use_fusion: bool
    use_ensemble: bool
    adaptive: bool

    # Fusion settings
    fusion_num_queries: int

    # Reranking
    reranker_model: str
    reranker_batch_size: int

    class Config:
        frozen = True


def get_retrieval_config() -> RetrievalConfig:
    """Create retrieval config from main settings"""
    settings = get_settings()

    return RetrievalConfig(
        top_k_initial=settings.retrieval_top_k_initial,
        top_k_final=settings.retrieval_top_k_final,
        confidence_threshold=settings.retrieval_confidence_threshold,
        vector_weight=settings.hybrid_vector_weight,
        keyword_weight=settings.hybrid_keyword_weight,
        use_hyde=settings.use_hyde,
        use_fusion=settings.use_fusion,
        use_ensemble=settings.use_ensemble,
        adaptive=settings.adaptive_retrieval,
        fusion_num_queries=settings.fusion_num_queries,
        reranker_model=settings.reranker_model,
        reranker_batch_size=settings.reranker_batch_size
    )


# Singleton
_retrieval_config = None


def get_config() -> RetrievalConfig:
    """Get or create retrieval config singleton"""
    global _retrieval_config
    if _retrieval_config is None:
        _retrieval_config = get_retrieval_config()
    return _retrieval_config