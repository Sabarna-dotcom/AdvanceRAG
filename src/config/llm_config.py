# src/llm/config/llm_config.py

"""
Configuration specific to the
LLM generation module.
"""

from pydantic import BaseModel

from src.config.settings import (
    get_settings
)


class LLMConfig(BaseModel):
    """
    Configuration for
    Ollama LLM generation.
    """

    # Ollama connection
    ollama_base_url: str

    # Model settings
    model_name: str
    temperature: float
    max_tokens: int
    timeout: int

    # Optional tracking
    track_costs: bool = False

    class Config:
        frozen = True


def get_llm_config() -> LLMConfig:
    """
    Create LLM config
    from main settings.
    """

    settings = get_settings()

    return LLMConfig(

        # Ollama
        ollama_base_url=(settings.ollama_base_url),

        # Model
        model_name=(settings.ollama_llm_model),
        temperature=(settings.ollama_temperature),
        max_tokens=(settings.ollama_max_tokens),
        timeout=(settings.ollama_timeout),

        # Tracking
        track_costs=(settings.track_costs)
    )


# ==========================================
# Singleton
# ==========================================

_llm_config = None


def get_config() -> LLMConfig:
    """
    Get or create
    LLM config singleton.
    """

    global _llm_config

    if _llm_config is None:

        _llm_config = (
            get_llm_config()
        )

    return _llm_config