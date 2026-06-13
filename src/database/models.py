# src/database/models.py
"""
SQLAlchemyORM models — mirrors the PostgreSQL schema in scripts/init_db.sqlexactly.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey,
    Integer, String, Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from src.database.connection import Base

# pgvectorcolumn type
try:
    from pgvector.sqlalchemy import Vector
    _VECTOR_AVAILABLE = True
except ImportError:
    _VECTOR_AVAILABLE = False
    Vector = None # fallback — columns will be skipped


def _now():
    return datetime.now(timezone.utc)


# ==========================================
# Authentication Tables
# ==========================================

class User(Base):
    __tablename__ = "users"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False)
    username = Column(String(100), unique=True, nullable=False)
    password_hash= Column(String(255), nullable=False)
    full_name  = Column(String(200))
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=_now)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)
    last_login = Column(DateTime(timezone=True))

    # Relationships
    auth_sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    conversation_metas= relationship("ConversationMeta", back_populates="user", cascade="all, delete-orphan")
    memory = relationship("UserMemory", back_populates="user", uselist=False, cascade="all, delete-orphan")
    topic_interests = relationship("UserTopicInterest", back_populates="user", cascade="all, delete-orphan")
    query_logs = relationship("QueryLog", back_populates="user")
    feedbacks = relationship("UserFeedback", back_populates="user", cascade="all, delete-orphan")


class UserSession(Base):
    """JWT auth sessions — one row per login (refresh token tracking)."""
    __tablename__ = "user_sessions"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(50), ForeignKey("users.id", ondelete="CASCADE"))
    token_hash = Column(String(255), nullable=False)
    device_info = Column(JSONB)
    ip_address = Column(String(50))
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now)
    last_activity= Column(DateTime(timezone=True), default=_now)

    user = relationship("User", back_populates="auth_sessions")


# ==========================================
# Conversation / Chat History Tables
# ==========================================

class Conversation(Base):
    """One row per message turn — the permanent chat history store."""
    __tablename__ = "conversations"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id= Column(String(50), nullable=False, index=True)
    user_id = Column(String(50), ForeignKey("users.id", ondelete="CASCADE"))
    role = Column(String(20), nullable=False) # user | assistant | system
    message = Column(Text, nullable=False)
    sources_used = Column(JSONB)
    extract_metadata = Column("metadata",JSONB)
    timestamp = Column(DateTime(timezone=True), default=_now)

    # Optional vector embedding for semantic history search
    if _VECTOR_AVAILABLE:
        embedding = Column(Vector(1024))

    user = relationship("User", back_populates="conversations")


class ConversationMeta(Base):
    """One row per conversation — title, summary, message count."""
    __tablename__ = "conversation_metadata"

    conversation_id= Column(String(50), primary_key=True)
    user_id = Column(String(50), ForeignKey("users.id", ondelete="CASCADE"))
    title = Column(String(500))
    summary = Column(Text)
    topic = Column(String(100))
    message_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=_now)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)
    last_message_at= Column(DateTime(timezone=True))
    is_archived = Column(Boolean, default=False)

    user = relationship("User", back_populates="conversation_metas")


# ==========================================
# Long-Term Memory Tables
# ==========================================

class UserMemory(Base):
    """One row per user — learning profile and preferences."""
    __tablename__ = "user_memory"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(50), ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    preferred_topics = Column(JSONB, default=list)
    learning_level = Column(String(50), default="intermediate")
    learning_style = Column(String(50))
    frequent_query_types = Column(JSONB, default=dict)
    preferred_source_types= Column(JSONB, default=list)
    avg_session_duration = Column(Integer)
    total_queries = Column(Integer, default=0)
    total_conversations = Column(Integer, default=0)
    helpful_responses = Column(Integer, default=0)
    not_helpful_responses= Column(Integer, default=0)
    custom_preferences = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=_now)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)

    user = relationship("User", back_populates="memory")


class UserTopicInterest(Base):
    """Topic interest scores — increases with repeated queries."""
    __tablename__ = "user_topic_interest"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(50), ForeignKey("users.id", ondelete="CASCADE"))
    topic = Column(String(200), nullable=False)
    interest_score = Column(Float, default=1.0)
    first_queried_at= Column(DateTime(timezone=True), default=_now)
    last_queried_at= Column(DateTime(timezone=True), default=_now)
    query_count = Column(Integer, default=1)

    user = relationship("User", back_populates="topic_interests")


class ConversationSummary(Base):
    """Compressed long-term memory — summary of past conversations."""
    __tablename__ = "conversation_summaries"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(50), ForeignKey("users.id", ondelete="CASCADE"))
    conversation_id = Column(String(50))
    summary_text = Column(Text, nullable=False)
    key_topics = Column(JSONB, default=list)
    insights_learned= Column(JSONB, default=list)
    created_at = Column(DateTime(timezone=True), default=_now)

    if _VECTOR_AVAILABLE:
        summary_embedding = Column(Vector(1024))

    user = relationship("User")


# ==========================================
# Analytics Tables
# ==========================================

class QueryLog(Base):
    """Every query logged permanently — for analytics and monitoring."""
    __tablename__ = "query_logs"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(50), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    conversation_id = Column(String(50))
    query = Column(Text, nullable=False)
    response = Column(Text)
    retrieval_strategy = Column(String(50))
    retrieval_confidence= Column(Float)
    retrieval_count = Column(Integer)
    sources_used = Column(JSONB)
    latency_ms = Column(Integer)
    cost_usd = Column(Float)
    ragas_scores = Column(JSONB)
    cache_hit = Column(Boolean, default=False)
    timestamp = Column(DateTime(timezone=True), default=_now)

    user = relationship("User", back_populates="query_logs")
    feedbacks = relationship("UserFeedback", back_populates="query_log", cascade="all, delete-orphan")


class UserFeedback(Base):
    """User ratings on individual responses."""
    __tablename__ = "user_feedback"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    query_log_id = Column(String(50), ForeignKey("query_logs.id", ondelete="CASCADE"))
    user_id = Column(String(50), ForeignKey("users.id", ondelete="CASCADE"))
    conversation_id= Column(String(50))
    rating = Column(Integer) # 1-5
    feedback_type= Column(String(20)) # helpful | not_helpful| incorrect | incomplete | excellent
    comment = Column(Text)
    timestamp = Column(DateTime(timezone=True), default=_now)

    query_log= relationship("QueryLog", back_populates="feedbacks")
    user = relationship("User", back_populates="feedbacks")


# SystemMetric
class SystemMetric(Base):
    __tablename__ = "system_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    metric_name = Column(String(100), nullable=False)
    metric_value = Column(Float, nullable=False)
    user_id = Column(
        String(50),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    metric_metadata = Column("metadata", JSONB)

    timestamp = Column(
        DateTime(timezone=True),
        default=_now
    )

    user = relationship("User")
