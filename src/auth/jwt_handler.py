# src/auth/jwt_handler.py
"""
JWT token creation, verification, and Redis-backed blacklist (for logout).

Access token — short-lived (30 min default)
Refresh token — long-lived (7 days default)

Logout: JTI (JWT ID) is stored in Redis with TTL = remaining token lifetime.
On every verify_token() call, the JTI is checked against the blacklist.
"""

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Tuple

from jose import JWTError, jwt
import redis

from src.config.auth_config import get_auth_config
from src.memory.memory_config import get_config as get_memory_config
from src.utils.logger import get_logger

logger = get_logger(__name__)


class JWTHandler:

    _BLACKLIST_PREFIX = "token_blacklist:{}"

    def __init__(self):
        self.config = get_auth_config()
        # Redis for blacklist
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
            logger.warning(f"JWTHandler: Redis unavailable — token blacklist disabled. {e}")
            self._redis = None
            self._redis_ok = False

    # ------------------------------------------
    # Token Creation
    # ------------------------------------------

    def create_access_token(self, user_id: str, email: str) -> Tuple[str, str]:
        """
        Create a signed access token.
        Returns (token_string, jti).
        """
        jti = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=self.config.access_token_expire_minutes)

        payload = {
            "sub": user_id,
            "email": email,
            "type": "access",
            "jti": jti,
            "iat": now,
            "exp": expire,
        }
        token = jwt.encode(
            payload,
            self.config.jwt_secret_key,
            algorithm=self.config.jwt_algorithm,
        )
        return token, jti

    def create_refresh_token(self, user_id: str, email: str) -> Tuple[str, str]:
        """
        Create a signed refresh token.
        Returns (token_string, jti).
        """
        jti = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        expire = now + timedelta(days=self.config.refresh_token_expire_days)

        payload = {
            "sub": user_id,
            "email": email,
            "type": "refresh",
            "jti": jti,
            "iat": now,
            "exp": expire,
        }
        token = jwt.encode(
            payload,
            self.config.jwt_secret_key,
            algorithm=self.config.jwt_algorithm,
        )
        return token, jti

    # ------------------------------------------
    # Token Verification
    # ------------------------------------------

    def verify_token(self, token: str, token_type: str = "access") -> Dict:
        """
        Decode and validate a JWT.
        Raises ValueError if invalid, expired, wrong type, or blacklisted.
        """
        try:
            payload = jwt.decode(
                token,
                self.config.jwt_secret_key,
                algorithms=[self.config.jwt_algorithm],
            )
        except JWTError as e:
            raise ValueError(f"Invalid token: {e}") from e

        if payload.get("type") != token_type:
            raise ValueError(
                f"Wrong token type. Expected '{token_type}', got '{payload.get('type')}'."
            )

        jti = payload.get("jti")
        if jti and self.is_blacklisted(jti):
            raise ValueError("Token has been revoked (logged out).")

        return payload

    # ------------------------------------------
    # Blacklist (logout support)
    # ------------------------------------------

    def blacklist_token(self, jti: str, ttl_seconds: int) -> None:
        """Store JTI in Redis blacklist with TTL = remaining token lifetime."""
        if not self._redis_ok or not self._redis:
            logger.warning("JWTHandler: cannot blacklist token — Redis unavailable.")
            return
        try:
            key = self._BLACKLIST_PREFIX.format(jti)
            self._redis.setex(key, max(ttl_seconds, 1), "1")
            logger.debug(f"JWTHandler: token blacklisted | jti={jti} ttl={ttl_seconds}s")
        except Exception as e:
            logger.error(f"JWTHandler: blacklist write failed — {e}")

    def is_blacklisted(self, jti: str) -> bool:
        """Return True if the JTI is in the Redis blacklist."""
        if not self._redis_ok or not self._redis:
            return False
        try:
            return self._redis.exists(self._BLACKLIST_PREFIX.format(jti)) == 1
        except Exception as e:
            logger.error(f"JWTHandler: blacklist read failed — {e}")
        return False

    # ------------------------------------------
    # Helpers
    # ------------------------------------------

    @staticmethod
    def hash_token(token: str) -> str:
        """SHA-256 hash of token string — used for storing refresh tokens in DB."""
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def get_remaining_ttl(payload: Dict) -> int:
        """Seconds until token expires. Returns 0 if already expired."""
        exp = payload.get("exp", 0)
        remaining = int(exp - datetime.now(timezone.utc).timestamp())
        return max(remaining, 0)

