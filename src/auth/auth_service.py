# src/auth/auth_service.py
"""
AuthService — business logic for register, login, refresh, and logout.

Features:
  - bcrypt password hashing
  - JWT access + refresh tokens
  - Redis-backed login attempt tracking + account lockout
  - Password policy enforcement (from settings)
  - Refresh token stored as SHA-256 hash in user_sessions table
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import redis
from sqlalchemy.orm import Session

from src.auth.password_handler import PasswordHandler
from src.auth.jwt_handler import JWTHandler
from src.config.auth_config import get_auth_config
from src.memory.memory_config import get_config as get_memory_config
from src.database.models import User, UserSession
from src.utils.logger import get_logger
from src.utils.exceptions import AppException

logger = get_logger(__name__)


# ==========================================
# Auth Exception
# ==========================================

class AuthException(AppException):
    """Raised for auth-specific errors (bad credentials, lockout, policy violations)."""
    pass


# ==========================================
# AuthService
# ==========================================

class AuthService:

    _ATTEMPTS_KEY = "login_attempts:{}"
    _LOCKOUT_KEY  = "login_lockout:{}"

    def __init__(self):
        self.config           = get_auth_config()
        self.password_handler = PasswordHandler()
        self.jwt_handler      = JWTHandler()

        # Redis for login attempt tracking
        try:
            mem_cfg = get_memory_config()
            self._redis = redis.Redis(
                host=mem_cfg.host,
                port=mem_cfg.port,
                password=mem_cfg.password or None,
                db=mem_cfg.db,
                decode_responses=True,
                socket_connect_timeout=2,
            )
            self._redis.ping()
            self._redis_ok = True
        except Exception as e:
            logger.warning(f"AuthService: Redis unavailable — lockout tracking disabled. {e}")
            self._redis    = None
            self._redis_ok = False

    # ------------------------------------------
    # Register
    # ------------------------------------------

    def register(
        self,
        db: Session,
        email: str,
        username: str,
        password: str,
        full_name: Optional[str] = None,
    ) -> User:
        """
        Register a new user.
        Raises AuthException on duplicate email/username or weak password.
        """
        email    = email.strip().lower()
        username = username.strip().lower()

        if db.query(User).filter(User.email == email).first():
            raise AuthException(message="Email is already registered.")
        if db.query(User).filter(User.username == username).first():
            raise AuthException(message="Username is already taken.")

        self._validate_password(password)

        user = User(
            id            = str(uuid.uuid4()),
            email         = email,
            username      = username,
            password_hash = self.password_handler.hash_password(password),
            full_name     = full_name,
            is_active     = True,
            is_verified   = False,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        logger.info(f"AuthService: registered | user_id={user.id} email={user.email}")
        return user

    # ------------------------------------------
    # Login
    # ------------------------------------------

    def login(
        self,
        db: Session,
        email: str,
        password: str,
        ip_address: Optional[str] = None,
    ) -> dict:
        """
        Authenticate user. Returns access + refresh tokens on success.
        Raises AuthException on bad credentials or lockout.
        """
        email = email.strip().lower()

        # 1. Check lockout BEFORE hitting DB (fast Redis check)
        self._check_lockout(email)

        # 2. Find user
        user = db.query(User).filter(User.email == email).first()

        # 3. Verify password (run even if user not found to prevent timing attacks)
        if not user or not self.password_handler.verify_password(password, user.password_hash):
            self._record_failed_attempt(email)
            raise AuthException(message="Invalid email or password.")

        if not user.is_active:
            raise AuthException(message="Account is disabled. Contact support.")

        # 4. Clear failed attempts on success
        self._clear_failed_attempts(email)

        # 5. Create tokens
        access_token,  _       = self.jwt_handler.create_access_token(user.id, user.email)
        refresh_token, _       = self.jwt_handler.create_refresh_token(user.id, user.email)

        # 6. Store refresh token hash in user_sessions
        auth_session = UserSession(
            id          = str(uuid.uuid4()),
            user_id     = user.id,
            token_hash  = self.jwt_handler.hash_token(refresh_token),
            ip_address  = ip_address,
            expires_at  = datetime.now(timezone.utc) + timedelta(days=self.config.refresh_token_expire_days),
        )
        db.add(auth_session)

        # 7. Update last_login
        user.last_login = datetime.now(timezone.utc)
        db.commit()

        logger.info(f"AuthService: login success | user_id={user.id}")
        return {
            "access_token":  access_token,
            "refresh_token": refresh_token,
            "token_type":    "bearer",
            "user_id":       user.id,
            "email":         user.email,
            "username":      user.username,
        }

    # ------------------------------------------
    # Refresh
    # ------------------------------------------

    def refresh_access_token(self, db: Session, refresh_token: str) -> dict:
        """Exchange a valid refresh token for a new access token."""
        try:
            payload = self.jwt_handler.verify_token(refresh_token, token_type="refresh")
        except ValueError as e:
            raise AuthException(message=f"Invalid refresh token: {e}")

        # Verify token exists in DB (wasn't revoked / expired)
        token_hash   = self.jwt_handler.hash_token(refresh_token)
        auth_session = db.query(UserSession).filter(
            UserSession.token_hash == token_hash,
            UserSession.expires_at  > datetime.now(timezone.utc),
        ).first()

        if not auth_session:
            raise AuthException(message="Refresh token is expired or was revoked.")

        user = db.query(User).filter(User.id == payload["sub"], User.is_active == True).first()
        if not user:
            raise AuthException(message="User not found or disabled.")

        # Issue new access token
        new_access_token, _ = self.jwt_handler.create_access_token(user.id, user.email)

        # Update session activity
        auth_session.last_activity = datetime.now(timezone.utc)
        db.commit()

        logger.info(f"AuthService: token refreshed | user_id={user.id}")
        return {"access_token": new_access_token, "token_type": "bearer"}

    # ------------------------------------------
    # Logout
    # ------------------------------------------

    def logout(self, db: Session, access_token: str) -> None:
        """
        Logout:
          1. Blacklist the access token JTI in Redis (immediate invalidation)
          2. Optionally clean up user_sessions (refresh tokens expire naturally)
        """
        try:
            payload = self.jwt_handler.verify_token(access_token, token_type="access")
            jti     = payload.get("jti")
            ttl     = self.jwt_handler.get_remaining_ttl(payload)

            if jti:
                self.jwt_handler.blacklist_token(jti, ttl)

            logger.info(f"AuthService: logout | user_id={payload.get('sub')}")

        except ValueError:
            # Token already invalid — logout anyway, no error
            logger.debug("AuthService: logout called with invalid token — ignoring.")

    # ------------------------------------------
    # User Lookups
    # ------------------------------------------

    def get_user_by_id(self, db: Session, user_id: str) -> Optional[User]:
        return db.query(User).filter(User.id == user_id, User.is_active == True).first()

    def get_user_by_email(self, db: Session, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email.lower()).first()

    # ------------------------------------------
    # Password Policy
    # ------------------------------------------

    def _validate_password(self, password: str) -> None:
        cfg = self.config
        if len(password) < cfg.password_min_length:
            raise AuthException(
                message=f"Password must be at least {cfg.password_min_length} characters."
            )
        if cfg.password_require_uppercase and not any(c.isupper() for c in password):
            raise AuthException(message="Password must contain at least one uppercase letter.")
        if cfg.password_require_numbers and not any(c.isdigit() for c in password):
            raise AuthException(message="Password must contain at least one number.")
        if cfg.password_require_special and not any(
            c in "!@#$%^&*()_+-=[]{}|;':\",./<>?" for c in password
        ):
            raise AuthException(message="Password must contain at least one special character.")

    # ------------------------------------------
    # Login Attempt Tracking (Redis)
    # ------------------------------------------

    def _check_lockout(self, email: str) -> None:
        if not self._redis_ok:
            return
        if self._redis.exists(self._LOCKOUT_KEY.format(email)):
            raise AuthException(
                message=(
                    f"Account temporarily locked due to too many failed login attempts. "
                    f"Try again in {self.config.lockout_duration_minutes} minutes."
                )
            )

    def _record_failed_attempt(self, email: str) -> None:
        if not self._redis_ok:
            return
        key   = self._ATTEMPTS_KEY.format(email)
        count = self._redis.incr(key)
        self._redis.expire(key, self.config.lockout_duration_minutes * 60)

        if int(count) >= self.config.max_login_attempts:
            lockout_key = self._LOCKOUT_KEY.format(email)
            self._redis.setex(
                lockout_key,
                self.config.lockout_duration_minutes * 60,
                "1",
            )
            raise AuthException(
                message=(
                    f"Too many failed login attempts. "
                    f"Account locked for {self.config.lockout_duration_minutes} minutes."
                )
            )

    def _clear_failed_attempts(self, email: str) -> None:
        if not self._redis_ok:
            return
        self._redis.delete(self._ATTEMPTS_KEY.format(email))
        self._redis.delete(self._LOCKOUT_KEY.format(email))
