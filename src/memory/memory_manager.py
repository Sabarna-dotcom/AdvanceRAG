# src/memory/memory_manager.py

"""
MemoryManager — Redis-backed session memory for chat history.

Responsibilities:
 - Create / load / save / delete chat history per session_id
 - Enforce max_chat_history window (trim oldest turns automatically)
 - TTL-based expiry (session expires after inactivity)
 - Generate new session IDs

Redis key structure:
    session:{session_id}:history -> JSON list of {role, content} dicts
    session:{session_id}:meta -> JSON dict with created_at, last_active, query_count

Usage:
    manager = MemoryManager()

    # Start or resume a session
    session_id = manager.create_session()  # new session
    history = manager.get_history(session_id)  # load existing

    # After getting a response, save updated history
    manager.append_turn(session_id, "user", "What is photosynthesis?")
    manager.append_turn(session_id, "assistant", "Photosynthesis is...")

    # Pass history to pipeline
    chunks = retriever.retrieve(query=query, chat_history=history)
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

import redis

from src.memory.memory_config import get_config
from src.utils.logger import get_logger
from src.utils.exceptions import AppException

logger = get_logger(__name__)


# ==========================================
# Memory Exception
# ==========================================

class MemoryException(AppException):
    """Raised for memory / Redis errors."""
    pass


# ==========================================
# MemoryManager
# ==========================================

class MemoryManager:
    """
    Manages per-session chat history in Redis.

    Each session stores:
      - history : list of {role, content} turns (trimmed to max_chat_history)
      - meta    : {created_at, last_active, query_count}
    """

    # Redis key prefixes
    _HISTORY_PREFIX = "session:{}:history"
    _META_PREFIX = "session:{}:meta"

    def __init__(self):
        # Always initialize to None first so the attribute always exists
        self.client = None
        self.config = None
        self.ttl = 3600  # fallback: 1 hour
        self.max_history = 10  # fallback: 10 turns

        try:
            self.config = get_config()

            self.ttl = self.config.ttl_session
            self.max_history = self.config.max_chat_history

            self.client = redis.Redis(
                host=self.config.host,
                port=self.config.port,
                password=self.config.password or None,
                db=self.config.db,
                decode_responses=True,
            )

            # Quick connectivity check
            self.client.ping()

            logger.info(
                f"MemoryManager initialized | "
                f"host={self.config.host}:{self.config.port} | "
                f"ttl={self.ttl}s | max_history={self.max_history}"
            )

        except redis.exceptions.ConnectionError as e:
            logger.exception("MemoryManager: Redis connection failed.")
            raise MemoryException(
                message="Redis connection failed — is Redis running? (docker-compose up redis)",
                details=str(e),
            ) from e

        except Exception as e:
            logger.exception("MemoryManager initialization failed.")
            raise MemoryException(
                message="MemoryManager init failed",
                details=str(e),
            ) from e

    def _check_client(self):
        """Guard — raise clearly if Redis client is not available."""
        if self.client is None:
            raise MemoryException(
                message="Redis client is not initialized. MemoryManager.__init__ may have failed."
            )


# ------------------------------------------
# Session Management
# ------------------------------------------

    def create_session(self) -> str:
        self._check_client()

        session_id = str(uuid.uuid4())

        now = datetime.now(timezone.utc).isoformat()

        meta = {
            "created_at": now,
            "last_active": now,
            "query_count": 0,
        }

        history_key = self._HISTORY_PREFIX.format(session_id)
        meta_key = self._META_PREFIX.format(session_id)

        pipe = self.client.pipeline()
        pipe.set(history_key, json.dumps([]), ex=self.ttl)
        pipe.set(meta_key, json.dumps(meta), ex=self.ttl)
        pipe.execute()

        logger.info(
            f"MemoryManager: new session created | session_id={session_id}"
        )

        return session_id


    def session_exists(self, session_id: str) -> bool:
        """Check if a session is still alive in Redis."""
        self._check_client()

        history_key = self._HISTORY_PREFIX.format(session_id)

        return self.client.exists(history_key) == 1


    def delete_session(self, session_id: str) -> None:
        """Explicitly delete a session and all its data from Redis."""
        self._check_client()

        pipe = self.client.pipeline()
        pipe.delete(self._HISTORY_PREFIX.format(session_id))
        pipe.delete(self._META_PREFIX.format(session_id))
        pipe.execute()

        logger.info(
            f"MemoryManager: session deleted | session_id={session_id}"
        )


# ------------------------------------------
# History Read / Write
# ------------------------------------------

    def get_history(self, session_id: str) -> List[Dict]:
        """
        Load full chat history for a session.
        Returns empty list if session not found.
        """
        self._check_client()

        history_key = self._HISTORY_PREFIX.format(session_id)

        raw = self.client.get(history_key)

        if raw is None:
            logger.warning(
                f"MemoryManager: session not found or expired | "
                f"session_id={session_id}"
            )
            return []

        history = json.loads(raw)

        logger.debug(
            f"MemoryManager: loaded history | "
            f"session_id={session_id} | turns={len(history)}"
        )

        return history


    def save_history(self, session_id: str, history: List[Dict]) -> None:
        """Overwrite the full history for a session. Trims and refreshes TTL."""
        self._check_client()

        if len(history) > self.max_history:
            history = history[-self.max_history:]

        history_key = self._HISTORY_PREFIX.format(session_id)

        self.client.set(
            history_key,
            json.dumps(history),
            ex=self.ttl,
        )

        logger.debug(
            f"MemoryManager: history saved | "
            f"session_id={session_id} | turns={len(history)}"
        )


    def append_turn(
        self,
        session_id: str,
        role: str,
        content: str,
    ) -> List[Dict]:
        """
        Append a single turn to the session history.
        Creates session automatically if it doesn't exist yet.
        """

        if role not in ("user", "assistant"):
            raise MemoryException(
                message=f"Invalid role '{role}' — must be 'user' or 'assistant'"
            )

        # Load existing or start fresh
        if self.session_exists(session_id):
            history = self.get_history(session_id)
        else:
            logger.info(
                f"MemoryManager: auto-creating session | session_id={session_id}"
            )

            # BUG: create_session() returns a NEW UUID
            # self.create_session()

            history = []

        history.append(
            {
                "role": role,
                "content": content,
            }
        )

        self.save_history(session_id, history)

        self._update_meta(session_id, role)

        return history


    def append_exchange(
        self,
        session_id: str,
        user_query: str,
        assistant_answer: str,
    ) -> List[Dict]:
        """
        Convenience method — append both user query and assistant answer.
        """

        if self.session_exists(session_id):
            history = self.get_history(session_id)
        else:
            # BUG: create_session() returns a NEW UUID
            # self.create_session()

            history = []

        history.append(
            {
                "role": "user",
                "content": user_query,
            }
        )

        history.append(
            {
                "role": "assistant",
                "content": assistant_answer,
            }
        )

        self.save_history(session_id, history)

        self._update_meta(session_id, "assistant")

        logger.info(
            f"MemoryManager: exchange saved | "
            f"session_id={session_id} | total_turns={len(history)}"
        )

        return history


# ------------------------------------------
# Session Metadata
# ------------------------------------------

    def get_meta(self, session_id: str) -> Optional[Dict]:
        """Get session metadata. Returns None if session not found."""
        self._check_client()

        meta_key = self._META_PREFIX.format(session_id)

        raw = self.client.get(meta_key)

        if raw is None:
            return None

        return json.loads(raw)


    def _update_meta(self, session_id: str, role: str) -> None:
        """Update last_active timestamp and increment query_count."""
        self._check_client()

        meta_key = self._META_PREFIX.format(session_id)

        raw = self.client.get(meta_key)

        if raw is None:
            return

        meta = json.loads(raw)

        meta["last_active"] = datetime.now(timezone.utc).isoformat()

        if role == "user":
            meta["query_count"] = meta.get("query_count", 0) + 1

        self.client.set(
            meta_key,
            json.dumps(meta),
            ex=self.ttl,
        )


    def clear_history(self, session_id: str) -> None:
        """Clear chat history for a session but keep the session alive."""
        self._check_client()

        history_key = self._HISTORY_PREFIX.format(session_id)

        self.client.set(
            history_key,
            json.dumps([]),
            ex=self.ttl,
        )

        logger.info(
            f"MemoryManager: history cleared | session_id={session_id}"
        )


    def get_recent_history(
        self,
        session_id: str,
        last_n: int = 4,
    ) -> List[Dict]:
        """
        Return only the last N turns of history.
        Useful for passing a short context window to the LLM.
        """

        history = self.get_history(session_id)

        return history[-last_n:] if len(history) > last_n else history