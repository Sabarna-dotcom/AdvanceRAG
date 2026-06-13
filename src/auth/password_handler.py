import bcrypt
from src.utils.logger import get_logger

logger = get_logger(__name__)

class PasswordHandler:

    def hash_password(self, password: str) -> str:
        hashed = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt()
        )
        return hashed.decode("utf-8")

    def verify_password(
        self,
        plain_password: str,
        hashed_password: str
    ) -> bool:
        try:
            return bcrypt.checkpw(
                plain_password.encode("utf-8"),
                hashed_password.encode("utf-8")
            )
        except Exception as e:
            logger.warning(
                f"PasswordHandler verification error: {e}"
            )
            return False