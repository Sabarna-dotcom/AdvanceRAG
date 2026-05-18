# config/guardrails_config.py
"""
Configuration specific to the guardrails module.
"""

from pydantic import BaseModel
from src.config.settings import get_settings


class InputGuardrailsConfig(BaseModel):
    """Configuration for input validation"""
    max_query_length: int
    min_query_length: int
    enable_content_filter: bool
    enable_prompt_injection_detection: bool

    class Config:
        frozen = True


class OutputGuardrailsConfig(BaseModel):
    """Configuration for output validation"""
    enable_hallucination_detection: bool
    hallucination_threshold: float
    enable_citation_validation: bool
    enable_academic_integrity: bool

    class Config:
        frozen = True


class RateLimitConfig(BaseModel):
    """Configuration for rate limiting"""
    per_user_hour: int
    per_user_day: int

    class Config:
        frozen = True


class GuardrailsConfig(BaseModel):
    """Combined guardrails configuration"""
    input: InputGuardrailsConfig
    output: OutputGuardrailsConfig
    rate_limit: RateLimitConfig

    class Config:
        frozen = True


def get_guardrails_config() -> GuardrailsConfig:
    """Create guardrails config from main settings"""
    settings = get_settings()

    input_config = InputGuardrailsConfig(
        max_query_length=settings.max_query_length,
        min_query_length=settings.min_query_length,
        enable_content_filter=settings.enable_content_filter,
        enable_prompt_injection_detection=settings.enable_prompt_injection_detection
    )

    output_config = OutputGuardrailsConfig(
        enable_hallucination_detection=settings.enable_hallucination_detection,
        hallucination_threshold=settings.hallucination_threshold,
        enable_citation_validation=settings.enable_citation_validation,
        enable_academic_integrity=settings.enable_academic_integrity
    )

    rate_limit_config = RateLimitConfig(
        per_user_hour=settings.rate_limit_per_user_hour,
        per_user_day=settings.rate_limit_per_user_day
    )

    return GuardrailsConfig(
        input=input_config,
        output=output_config,
        rate_limit=rate_limit_config
    )


# Singleton
_guardrails_config = None


def get_config() -> GuardrailsConfig:
    """Get or create guardrails config singleton"""
    global _guardrails_config
    if _guardrails_config is None:
        _guardrails_config = get_guardrails_config()
    return _guardrails_config