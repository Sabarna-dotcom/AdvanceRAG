# config/settings.py
"""
Main configuration file using Pydantic BaseSettings.
All environment variables are loaded here and validated.
"""

from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import Optional
import os


class Settings(BaseSettings):
    """Main application settings - loads from .env file"""

    # ============ OLLAMA EMBEDDINGS ============
    embedding_model: str = Field(default="bge-m3",env="EMBEDDING_MODEL")
    embedding_dimension: int = Field(default=1024,env="EMBEDDING_DIMENSION")
    embedding_batch_size: int = Field(default=32,env="EMBEDDING_BATCH_SIZE")
    embedding_max_retries: int = Field(default=3,env="EMBEDDING_MAX_RETRIES")
    embedding_timeout: int = Field(default=30,env="EMBEDDING_TIMEOUT")

    # ============ OLLAMA LLM ============
    ollama_base_url: str = Field(default="http://localhost:11434",env="OLLAMA_BASE_URL")
    ollama_llm_model: str = Field(default="llama3",env="OLLAMA_LLM_MODEL")
    ollama_temperature: float = Field(default=0.3,env="OLLAMA_TEMPERATURE")
    ollama_max_tokens: int = Field(default=1500,env="OLLAMA_MAX_TOKENS")
    ollama_timeout: int = Field(default=60,env="OLLAMA_TIMEOUT")
    llm_max_retries: int = Field(default=3,env="LLM_MAX_RETRIES")

    # ============ AUTHENTICATION ============
    jwt_secret_key: str = Field(...,env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256",env="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=30,env="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7,env="REFRESH_TOKEN_EXPIRE_DAYS")

    # Password policy
    password_min_length: int = Field(default=8,env="PASSWORD_MIN_LENGTH")
    password_require_special: bool = Field(default=True,env="PASSWORD_REQUIRE_SPECIAL")
    password_require_numbers: bool = Field(default=True,env="PASSWORD_REQUIRE_NUMBERS")
    password_require_uppercase: bool = Field(default=True,env="PASSWORD_REQUIRE_UPPERCASE")

    # Session management
    max_sessions_per_user: int = Field(default=5,env="MAX_SESSIONS_PER_USER")
    session_timeout_minutes: int = Field(default=60,env="SESSION_TIMEOUT_MINUTES")

    # Security settings
    enable_2fa: bool = Field(default=False,env="ENABLE_2FA")
    max_login_attempts: int = Field(default=5,env="MAX_LOGIN_ATTEMPTS")
    lockout_duration_minutes: int = Field(default=15,env="LOCKOUT_DURATION_MINUTES")

    # ============ PINECONE VECTOR DATABASE ============
    pinecone_api_key: str = Field(..., env="PINECONE_API_KEY")
    pinecone_environment: str = Field(default="us-west1-gcp", env="PINECONE_ENVIRONMENT")
    pinecone_index_name: str = Field(default="educational-rag", env="PINECONE_INDEX_NAME")
    pinecone_dimension: int = Field(default=1024, env="PINECONE_DIMENSION")
    pinecone_metric: str = Field(default="cosine", env="PINECONE_METRIC")
    pinecone_namespace_pdf: str = Field(default="pdf-chunks", env="PINECONE_NAMESPACE_PDF")
    pinecone_namespace_video: str = Field(default="video-transcripts", env="PINECONE_NAMESPACE_VIDEO")

    # ============ REDIS CACHE ============
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_password: str = Field(default="", env="REDIS_PASSWORD")
    redis_db: int = Field(default=0, env="REDIS_DB")
    redis_url: Optional[str] = Field(default=None, env="REDIS_URL")

    cache_ttl_query: int = Field(default=86400, env="CACHE_TTL_QUERY")
    cache_ttl_embedding: int = Field(default=604800, env="CACHE_TTL_EMBEDDING")
    cache_similarity_threshold: float = Field(default=0.95, env="CACHE_SIMILARITY_THRESHOLD")

    # ============ POSTGRESQL DATABASE ============
    database_url: str = Field(..., env="DATABASE_URL")
    database_pool_size: int = Field(default=5, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=10, env="DATABASE_MAX_OVERFLOW")

    # ============ RETRIEVAL CONFIGURATION ============
    retrieval_top_k_initial: int = Field(default=20, env="RETRIEVAL_TOP_K_INITIAL")
    retrieval_top_k_final: int = Field(default=5, env="RETRIEVAL_TOP_K_FINAL")
    retrieval_confidence_threshold: float = Field(default=0.6, env="RETRIEVAL_CONFIDENCE_THRESHOLD")

    hybrid_vector_weight: float = Field(default=0.7, env="HYBRID_VECTOR_WEIGHT")
    hybrid_keyword_weight: float = Field(default=0.3, env="HYBRID_KEYWORD_WEIGHT")

    use_hyde: bool = Field(default=True, env="USE_HYDE")
    use_fusion: bool = Field(default=True, env="USE_FUSION")
    use_ensemble: bool = Field(default=False, env="USE_ENSEMBLE")
    fusion_num_queries: int = Field(default=3, env="FUSION_NUM_QUERIES")
    adaptive_retrieval: bool = Field(default=True, env="ADAPTIVE_RETRIEVAL")

    reranker_model: str = Field(default="cross-encoder/ms-marco-MiniLM-L-12-v2", env="RERANKER_MODEL")
    reranker_batch_size: int = Field(default=16, env="RERANKER_BATCH_SIZE")

    # ============ CHUNKING CONFIGURATION ============
    pdf_chunk_size: int = Field(default=800, env="PDF_CHUNK_SIZE")
    pdf_chunk_overlap: int = Field(default=100, env="PDF_CHUNK_OVERLAP")
    pdf_enable_parent_child: bool = Field(default=True, env="PDF_ENABLE_PARENT_CHILD")
    pdf_parent_size: int = Field(default=1000, env="PDF_PARENT_SIZE")
    pdf_child_size: int = Field(default=300, env="PDF_CHILD_SIZE")

    video_chunk_duration: int = Field(default=180, env="VIDEO_CHUNK_DURATION")
    video_min_chunk_length: int = Field(default=50, env="VIDEO_MIN_CHUNK_LENGTH")
    video_enable_parent_child: bool = Field(default=True, env="VIDEO_ENABLE_PARENT_CHILD")

    # ============ GUARDRAILS ============
    max_query_length: int = Field(default=500, env="MAX_QUERY_LENGTH")
    min_query_length: int = Field(default=3, env="MIN_QUERY_LENGTH")
    enable_content_filter: bool = Field(default=True, env="ENABLE_CONTENT_FILTER")
    enable_prompt_injection_detection: bool = Field(default=True, env="ENABLE_PROMPT_INJECTION_DETECTION")

    enable_hallucination_detection: bool = Field(default=True, env="ENABLE_HALLUCINATION_DETECTION")
    hallucination_threshold: float = Field(default=0.15, env="HALLUCINATION_THRESHOLD")
    enable_citation_validation: bool = Field(default=True, env="ENABLE_CITATION_VALIDATION")
    enable_academic_integrity: bool = Field(default=True, env="ENABLE_ACADEMIC_INTEGRITY")

    rate_limit_per_user_hour: int = Field(default=100, env="RATE_LIMIT_PER_USER_HOUR")
    rate_limit_per_user_day: int = Field(default=1000, env="RATE_LIMIT_PER_USER_DAY")

    # ============ EVALUATION ============
    enable_ragas_eval: bool = Field(default=True, env="ENABLE_RAGAS_EVAL")
    ragas_sample_rate: float = Field(default=0.1, env="RAGAS_SAMPLE_RATE")
    ragas_async: bool = Field(default=True, env="RAGAS_ASYNC")

    # ============ LOGGING & MONITORING ============
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")
    log_file: str = Field(default="logs/rag.logs", env="LOG_FILE")

    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    metrics_port: int = Field(default=9090, env="METRICS_PORT")

    # ============ APPLICATION SETTINGS ============
    app_env: str = Field(default="development", env="APP_ENV")
    debug: bool = Field(default=True, env="DEBUG")
    max_chat_history: int = Field(default=10, env="MAX_CHAT_HISTORY")

    # ============ COST TRACKING ============
    track_costs: bool = Field(default=True, env="TRACK_COSTS")
    groq_cost_per_1k_tokens: float = Field(default=0.0001, env="GROQ_COST_PER_1K_TOKENS")
    embedding_cost_per_1k: float = Field(default=0.00002, env="EMBEDDING_COST_PER_1K")

    @validator("ollama_temperature")
    def validate_temperature(cls, v):
        """Ensure temperature is between 0 and 2"""
        if not 0 <= v <= 1:
            raise ValueError("Temperature must be between 0 and 2")
        return v

    @validator("hybrid_vector_weight", "hybrid_keyword_weight")
    def validate_weights(cls, v):
        """Ensure weights are between 0 and 1"""
        if not 0 <= v <= 1:
            raise ValueError("Weights must be between 0 and 1")
        return v

    @validator("redis_url", always=True)
    def construct_redis_url(cls, v, values):
        """Construct Redis URL if not provided"""
        if v:
            return v

        password = values.get("redis_password", "")
        host = values.get("redis_host", "localhost")
        port = values.get("redis_port", 6379)
        db = values.get("redis_db", 0)

        if password:
            return f"redis://:{password}@{host}:{port}/{db}"
        else:
            return f"redis://{host}:{port}/{db}"

    @validator("password_min_length")
    def validate_password_length(cls, v):
        if v < 6:
            raise ValueError("Password minimum length must be >= 6")
        return v

    @validator("max_login_attempts")
    def validate_login_attempts(cls, v):
        if v < 1:
            raise ValueError("Max login attempts must be positive")
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Singleton instance
_settings = None


def get_settings() -> Settings:
    """Get or create settings singleton"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


# Convenience function for quick access
settings = get_settings()