# src/memory/postgres_memory.py
"""
PostgresMemory — permanent long-term conversation storage in PostgreSQL.

Responsibilities:
  - Save every message turn permanently (conversations table)
  - Create/update conversation metadata (conversation_metadata table)
  - Restore Redis session from PostgreSQL when TTL expires
  - Save query logs for analytics (query_logs table)
  - Track user topic interests (user_topic_interest table)
  - Get user's past conversations list

Fails gracefully if PostgreSQL is unavailable — never crashes the API.
MemoryManager wraps this and calls it alongside Redis writes.
"""

import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.utils.logger import get_logger

logger = get_logger(__name__)


class PostgresMemory:
    """
    Long-term PostgreSQL-backed memory.

    is_available — False if PostgreSQL unreachable.
    All methods silently no-op when unavailable.
    """

    def __init__(self):
        self._available   = False
        self._SessionLocal = None

        try:
            from src.database.connection import get_session_factory
            from sqlalchemy import text

            self._SessionLocal = get_session_factory()

            # Quick connectivity check
            with self._session() as s:
                s.execute(text("SELECT 1"))

            self._available = True
            logger.info("PostgresMemory initialized — PostgreSQL connected.")

        except Exception as e:
            logger.warning(
                f"PostgresMemory: PostgreSQL not available — long-term memory disabled. {e}"
            )

    @property
    def is_available(self) -> bool:
        return self._available

    # ------------------------------------------
    # Internal session context manager
    # ------------------------------------------

    @contextmanager
    def _session(self):
        session = self._SessionLocal()
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # ==========================================
    # Message Storage
    # ==========================================

    def save_message(
        self,
        conversation_id: str,
        user_id: Optional[str],
        role: str,
        content: str,
        sources: Optional[Any] = None,
    ) -> None:
        """
        Permanently save one message turn.
        Also triggers conversation_metadata update (via PostgreSQL trigger).
        """
        if not self._available:
            return
        try:
            from src.database.models import Conversation
            with self._session() as s:
                msg = Conversation(
                    id              = str(uuid.uuid4()),
                    conversation_id = conversation_id,
                    user_id         = user_id,
                    role            = role,
                    message         = content,
                    sources_used    = sources if isinstance(sources, (dict, list)) else None,
                    timestamp       = datetime.now(timezone.utc),
                )
                s.add(msg)
                s.commit()
        except Exception as e:
            logger.error(f"PostgresMemory.save_message failed: {e}")

    def get_conversation_history(
        self,
        conversation_id: str,
        limit: int = 20,
    ) -> List[Dict]:
        """
        Load conversation history from PostgreSQL.
        Returns list of {role, content} dicts ordered oldest-first.
        """
        if not self._available:
            return []
        try:
            from src.database.models import Conversation
            with self._session() as s:
                rows = (
                    s.query(Conversation)
                    .filter(Conversation.conversation_id == conversation_id)
                    .order_by(Conversation.timestamp.asc())
                    .limit(limit)
                    .all()
                )
                return [{"role": r.role, "content": r.message} for r in rows]
        except Exception as e:
            logger.error(f"PostgresMemory.get_conversation_history failed: {e}")
            return []

    # ==========================================
    # Conversation Metadata
    # ==========================================

    def create_conversation(
        self,
        conversation_id: str,
        user_id: Optional[str],
        title: Optional[str] = None,
    ) -> None:
        """
        Create conversation_metadata row.
        Skipped if user_id is None (anonymous session).
        """
        if not self._available or not user_id:
            return
        try:
            from src.database.models import ConversationMeta
            with self._session() as s:
                existing = s.query(ConversationMeta).filter(
                    ConversationMeta.conversation_id == conversation_id
                ).first()
                if not existing:
                    s.add(ConversationMeta(
                        conversation_id = conversation_id,
                        user_id         = user_id,
                        title           = title,
                        created_at      = datetime.now(timezone.utc),
                        updated_at      = datetime.now(timezone.utc),
                    ))
                    s.commit()
        except Exception as e:
            logger.error(f"PostgresMemory.create_conversation failed: {e}")

    def get_user_conversations(
        self,
        user_id: str,
        limit: int = 20,
        include_archived: bool = False,
    ) -> List[Dict]:
        """
        Return list of conversations for a user, most recent first.
        Used by the frontend to show conversation history.
        """
        if not self._available:
            return []
        try:
            from src.database.models import ConversationMeta
            with self._session() as s:
                q = s.query(ConversationMeta).filter(ConversationMeta.user_id == user_id)
                if not include_archived:
                    q = q.filter(ConversationMeta.is_archived == False)
                rows = q.order_by(ConversationMeta.updated_at.desc()).limit(limit).all()
                return [
                    {
                        "conversation_id":  r.conversation_id,
                        "title":            r.title,
                        "message_count":    r.message_count,
                        "created_at":       r.created_at.isoformat() if r.created_at else None,
                        "last_message_at":  r.last_message_at.isoformat() if r.last_message_at else None,
                        "is_archived":      r.is_archived,
                    }
                    for r in rows
                ]
        except Exception as e:
            logger.error(f"PostgresMemory.get_user_conversations failed: {e}")
            return []

    # ==========================================
    # Redis Restore (on session expiry)
    # ==========================================

    def restore_to_redis(
        self,
        conversation_id: str,
        memory_manager,
        limit: int = 20,
    ) -> List[Dict]:
        """
        Load history from PostgreSQL and reseed Redis.

        Called by MemoryManager.get_history() when Redis returns empty
        for a conversation that may have expired.

        Returns:
            Restored history list (empty if nothing found in PostgreSQL).
        """
        if not self._available:
            return []

        history = self.get_conversation_history(conversation_id, limit=limit)
        if not history:
            return []

        try:
            memory_manager._create_session_with_id(conversation_id)
            memory_manager.save_history(conversation_id, history)
            logger.info(
                f"PostgresMemory: restored {len(history)} turns to Redis | "
                f"conversation_id={conversation_id}"
            )
        except Exception as e:
            logger.error(f"PostgresMemory.restore_to_redis failed: {e}")

        return history

    # ==========================================
    # Query Logs
    # ==========================================

    def save_query_log(
        self,
        conversation_id: str,
        query: str,
        user_id:            Optional[str] = None,
        response:           Optional[str] = None,
        retrieval_strategy: Optional[str] = None,
        retrieval_count:    Optional[int] = None,
        sources_used:       Optional[Any] = None,
        latency_ms:         Optional[int] = None,
        cache_hit:          bool          = False,
    ) -> None:
        """Save query log entry for analytics and monitoring."""
        if not self._available:
            return
        try:
            from src.database.models import QueryLog
            with self._session() as s:
                log = QueryLog(
                    id                 = str(uuid.uuid4()),
                    user_id            = user_id,
                    conversation_id    = conversation_id,
                    query              = query,
                    response           = response,
                    retrieval_strategy = retrieval_strategy,
                    retrieval_count    = retrieval_count,
                    sources_used       = sources_used if isinstance(sources_used, (dict, list)) else None,
                    latency_ms         = latency_ms,
                    cache_hit          = cache_hit,
                    timestamp          = datetime.now(timezone.utc),
                )
                s.add(log)
                s.commit()
        except Exception as e:
            logger.error(f"PostgresMemory.save_query_log failed: {e}")

    # ==========================================
    # Topic Interest Tracking
    # ==========================================

    def update_topic_interest(self, user_id: str, topic: str) -> None:
        """
        Upsert a topic interest record.
        interest_score increases with repeated queries (capped at 10.0).
        """
        if not self._available or not user_id:
            return
        try:
            from src.database.models import UserTopicInterest
            with self._session() as s:
                existing = s.query(UserTopicInterest).filter(
                    UserTopicInterest.user_id == user_id,
                    UserTopicInterest.topic   == topic,
                ).first()

                now = datetime.now(timezone.utc)
                if existing:
                    existing.query_count    += 1
                    existing.interest_score  = min(existing.interest_score + 0.1, 10.0)
                    existing.last_queried_at = now
                else:
                    s.add(UserTopicInterest(
                        id               = str(uuid.uuid4()),
                        user_id          = user_id,
                        topic            = topic,
                        interest_score   = 1.0,
                        first_queried_at = now,
                        last_queried_at  = now,
                        query_count      = 1,
                    ))
                s.commit()
        except Exception as e:
            logger.error(f"PostgresMemory.update_topic_interest failed: {e}")

    def get_user_top_topics(self, user_id: str, limit: int = 10) -> List[Dict]:
        """Return user's top topics sorted by interest score."""
        if not self._available:
            return []
        try:
            from src.database.models import UserTopicInterest
            with self._session() as s:
                rows = (
                    s.query(UserTopicInterest)
                    .filter(UserTopicInterest.user_id == user_id)
                    .order_by(UserTopicInterest.interest_score.desc())
                    .limit(limit)
                    .all()
                )
                return [
                    {
                        "topic":          r.topic,
                        "interest_score": r.interest_score,
                        "query_count":    r.query_count,
                        "last_queried_at": r.last_queried_at.isoformat() if r.last_queried_at else None,
                    }
                    for r in rows
                ]
        except Exception as e:
            logger.error(f"PostgresMemory.get_user_top_topics failed: {e}")
            return []

    # ==========================================
    # User Long-Term Profile
    # ==========================================

    def get_user_memory(self, user_id: str) -> Optional[Dict]:
        """Return the user's long-term memory/profile."""
        if not self._available:
            return None
        try:
            from src.database.models import UserMemory
            with self._session() as s:
                mem = s.query(UserMemory).filter(UserMemory.user_id == user_id).first()
                if not mem:
                    return None
                return {
                    "user_id":               mem.user_id,
                    "preferred_topics":      mem.preferred_topics or [],
                    "learning_level":        mem.learning_level,
                    "learning_style":        mem.learning_style,
                    "total_queries":         mem.total_queries,
                    "total_conversations":   mem.total_conversations,
                    "frequent_query_types":  mem.frequent_query_types or {},
                    "preferred_source_types":mem.preferred_source_types or [],
                }
        except Exception as e:
            logger.error(f"PostgresMemory.get_user_memory failed: {e}")
            return None
