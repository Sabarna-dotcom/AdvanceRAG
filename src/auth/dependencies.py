# src/auth/dependencies.py
"""
FastAPI auth dependencies.

get_optional_user  — returns user dict if valid token present, None otherwise.
                     Use for routes that work with OR without auth.

get_current_user   — returns user dict, raises HTTP 401 if not authenticated.
                     Use for routes that REQUIRE login.

Usage:
    from src.auth.dependencies import get_current_user, get_optional_user

    @router.get("/protected")
    async def protected(user=Depends(get_current_user)):
        return {"user_id": user["user_id"]}

    @router.post("/query")
    async def query(user=Depends(get_optional_user)):
        user_id = user["user_id"] if user else None
"""

from typing import Optional

from fastapi import Depends, HTTPException, Request

from src.auth.jwt_handler import JWTHandler
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def get_optional_user(request: Request) -> Optional[dict]:
    """
    Extract user from Bearer token if present.
    Returns None (does NOT raise) if:
      - No Authorization header
      - Token is invalid / expired / blacklisted
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None

    token = auth_header[7:].strip()
    if not token:
        return None

    try:
        handler = JWTHandler()
        payload = handler.verify_token(token, token_type="access")
        return {
            "user_id": payload["sub"],
            "email":   payload.get("email"),
            "jti":     payload.get("jti"),
            "token":   token,
        }
    except ValueError as e:
        logger.debug(f"get_optional_user: token rejected — {e}")
        return None


async def get_current_user(user: Optional[dict] = Depends(get_optional_user)) -> dict:
    """
    Required auth dependency — raises HTTP 401 if no valid token.
    """
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please login via POST /auth/login.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
