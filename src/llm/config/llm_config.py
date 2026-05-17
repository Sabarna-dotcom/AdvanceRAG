# config/llm_config.py
"""
Configuration specific to the LLM generation module.
"""

from pydantic import BaseModel
from src.config.settings import get_settings


class LLMConfig(BaseModel):
    """Configuration for LLM (Groq) generation"""

    # API credentials
    api_key: str

    # Model settings
    model: str
    temperature: float
    max_tokens: int
    timeout: int

    # Cost tracking
    cost_per_1k_tokens: float
    track_costs: bool

    class Config:
        frozen = True


def get_llm_config() -> LLMConfig:
    """Create LLM config from main settings"""
    settings = get_settings()

    return LLMConfig(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        temperature=settings.groq_temperature,
        max_tokens=settings.groq_max_tokens,
        timeout=settings.groq_timeout,
        cost_per_1k_tokens=settings.groq_cost_per_1k_tokens,
        track_costs=settings.track_costs
    )


# Singleton
_llm_config = None


def get_config() -> LLMConfig:
    """Get or create LLM config singleton"""
    global _llm_config
    if _llm_config is None:
        _llm_config = get_llm_config()
    return _llm_config