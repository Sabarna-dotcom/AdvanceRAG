# src/utils/exceptions.py

"""
Custom application exceptions.
"""

from typing import Optional


class AppException(Exception):
    """
    Base application exception.
    """

    def __init__(
        self,
        message: str,
        details: Optional[str] = None
    ):

        self.message = message
        self.details = details

        super().__init__(
            self.__str__()
        )

    def __str__(self) -> str:

        if self.details:

            return (
                f"{self.message} "
                f"| Details: {self.details}"
            )

        return self.message


# ==========================================
# Configuration Exceptions
# ==========================================

class ConfigException(AppException):
    """
    Raised for configuration errors.
    """
    pass


# ==========================================
# LLM Exceptions
# ==========================================

class LLMException(AppException):
    """
    Raised for LLM-related errors.
    """
    pass


# ==========================================
# Database Exceptions
# ==========================================

class DatabaseException(AppException):
    """
    Raised for database errors.
    """
    pass

# ==========================================
# Vector Store Exceptions
# ==========================================

class VectorStoreException(AppException):
    """
    Raised for vector database errors.
    """
    pass


# ==========================================
# Validation Exceptions
# ==========================================

class ValidationException(AppException):
    """
    Raised for validation errors.
    """
    pass

# ===========================================
# Generation Exceptions
# ===========================================

class GenerationException(AppException):
    """
    Raised for generation-layer errors.
    """

    pass