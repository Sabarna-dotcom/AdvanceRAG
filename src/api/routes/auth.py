# src/api/routes/auth.py
"""
Authentication routes.

Routes:
    POST /auth/register  — create new account
    POST /auth/login     — get access + refresh tokens
    POST /auth/refresh   — exchange refresh token for new access token
    POST /auth/logout    — blacklist current access token
    GET  /auth/me        — get current user profile
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from src.auth.auth_service import AuthService, AuthException
from src.auth.dependencies import get_current_user
from src.database.connection import get_db
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ==========================================
# Request / Response Models
# ==========================================

class RegisterRequest(BaseModel):
    email:     str            = Field(..., description="Email address")
    username:  str            = Field(..., description="Unique username")
    password:  str            = Field(..., description="Password (must meet policy)")
    full_name: Optional[str]  = Field(default=None, description="Full name (optional)")


class LoginRequest(BaseModel):
    email:    str = Field(..., description="Registered email address")
    password: str = Field(..., description="Account password")


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., description="Refresh token received at login")


class RegisterResponse(BaseModel):
    user_id:  str
    email:    str
    username: str
    message:  str = "Registration successful. You can now login."


class LoginResponse(BaseModel):
    access_token:  str
    refresh_token: str
    token_type:    str = "bearer"
    user_id:       str
    email:         str
    username:      str
    message:       str = "Login successful."


class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"


class MeResponse(BaseModel):
    user_id:   str
    email:     str
    username:  Optional[str] = None
    full_name: Optional[str] = None


class MessageResponse(BaseModel):
    message: str


# ==========================================
# Routes
# ==========================================

@router.post(
    "/auth/register",
    response_model=RegisterResponse,
    summary="Register",
    description="Create a new user account. Password must meet the configured policy.",
)
async def register(payload: RegisterRequest, db=Depends(get_db)) -> RegisterResponse:
    try:
        auth = AuthService()
        user = auth.register(
            db,
            email     = payload.email,
            username  = payload.username,
            password  = payload.password,
            full_name = payload.full_name,
        )
        logger.info(f"POST /auth/register | user_id={user.id}")
        return RegisterResponse(user_id=user.id, email=user.email, username=user.username)
    except AuthException as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error(f"POST /auth/register error: {e}")
        raise HTTPException(status_code=500, detail="Registration failed. Please try again.")


@router.post(
    "/auth/login",
    response_model=LoginResponse,
    summary="Login",
    description="Authenticate with email + password. Returns access token (30 min) and refresh token (7 days).",
)
async def login(payload: LoginRequest, request: Request, db=Depends(get_db)) -> LoginResponse:
    try:
        auth   = AuthService()
        ip     = request.client.host if request.client else None
        result = auth.login(db, payload.email, payload.password, ip_address=ip)
        logger.info(f"POST /auth/login | user_id={result['user_id']}")
        return LoginResponse(**result)
    except AuthException as e:
        raise HTTPException(status_code=401, detail=e.message)
    except Exception as e:
        logger.error(f"POST /auth/login error: {e}")
        raise HTTPException(status_code=500, detail="Login failed. Please try again.")


@router.post(
    "/auth/refresh",
    response_model=TokenResponse,
    summary="Refresh Token",
    description="Exchange a valid refresh token for a new access token.",
)
async def refresh_token(payload: RefreshRequest, db=Depends(get_db)) -> TokenResponse:
    try:
        auth   = AuthService()
        result = auth.refresh_access_token(db, payload.refresh_token)
        return TokenResponse(**result)
    except AuthException as e:
        raise HTTPException(status_code=401, detail=e.message)
    except Exception as e:
        logger.error(f"POST /auth/refresh error: {e}")
        raise HTTPException(status_code=500, detail="Token refresh failed.")


@router.post(
    "/auth/logout",
    response_model=MessageResponse,
    summary="Logout",
    description="Invalidate the current access token. Pass the token in the Authorization header.",
)
async def logout(
    request: Request,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
) -> MessageResponse:
    try:
        auth  = AuthService()
        token = current_user["token"]
        auth.logout(db, token)
        logger.info(f"POST /auth/logout | user_id={current_user['user_id']}")
        return MessageResponse(message="Logged out successfully.")
    except Exception as e:
        logger.error(f"POST /auth/logout error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/auth/me",
    response_model=MeResponse,
    summary="Get Current User",
    description="Returns the profile of the currently authenticated user.",
)
async def get_me(
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
) -> MeResponse:
    auth = AuthService()
    user = auth.get_user_by_id(db, current_user["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return MeResponse(
        user_id   = user.id,
        email     = user.email,
        username  = user.username,
        full_name = user.full_name,
    )
