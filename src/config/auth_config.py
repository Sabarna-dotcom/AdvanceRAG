# config/auth_config.py
"""
Configuration for authentication and session management.
"""

from pydantic import BaseModel
from src.config.settings import get_settings


class AuthConfig(BaseModel):
    """Configuration for authentication"""

    # JWT settings
    jwt_secret_key: str
    jwt_algorithm: str
    access_token_expire_minutes: int
    refresh_token_expire_days: int

    # Password settings
    password_min_length: int
    password_require_special: bool
    password_require_numbers: bool
    password_require_uppercase: bool

    # Session settings
    max_sessions_per_user: int
    session_timeout_minutes: int

    # Security
    enable_2fa: bool
    max_login_attempts: int
    lockout_duration_minutes: int

    class Config:
        frozen = True


def get_auth_config() -> AuthConfig:
    """Create auth config from main settings"""
    settings = get_settings()

    return AuthConfig(
        # JWT
        jwt_secret_key=settings.jwt_secret_key,
        jwt_algorithm=settings.jwt_algorithm,
        access_token_expire_minutes=settings.access_token_expire_minutes,
        refresh_token_expire_days=settings.refresh_token_expire_days,

        # Password
        password_min_length=settings.password_min_length,
        password_require_special=settings.password_require_special,
        password_require_numbers=settings.password_require_numbers,
        password_require_uppercase=settings.password_require_uppercase,

        # Session
        max_sessions_per_user=settings.max_sessions_per_user,
        session_timeout_minutes=settings.session_timeout_minutes,

        # Security
        enable_2fa=settings.enable_2fa,
        max_login_attempts=settings.max_login_attempts,
        lockout_duration_minutes=settings.lockout_duration_minutes
    )


# Singleton
_auth_config = None


def get_config() -> AuthConfig:
    """Get or create auth config singleton"""
    global _auth_config
    if _auth_config is None:
        _auth_config = get_auth_config()
    return _auth_config