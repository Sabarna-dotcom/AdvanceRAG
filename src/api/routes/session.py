"""
Session routes — manage Redis-backed chat memory sessions.

Routes:
    POST   /session              — create a new session
    GET    /session              — list user's past conversations (requires auth)
    GET    /session/{session_id} — get session info + history
    DELETE /session/{session_id} — delete a session (clear memory)
    POST   /session/{session_id}/clear — clear history but keep session alive
"""

from typing import List, Optional, Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.auth.dependencies import get_optional_user, get_current_user
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ==========================================
# Response Models
# ==========================================

class SessionCreateResponse(BaseModel):
    session_id: str = Field(..., description="Newly created session ID. Pass this in future /query requests.")
    message: str    = Field(default="Session created successfully.")


class SessionInfoResponse(BaseModel):
    session_id:  str            = Field(..., description="Session ID.")
    exists:      bool           = Field(..., description="True if session is alive in Redis.")
    history:     List[Dict]     = Field(default=[], description="Full chat history for this session.")
    meta:        Optional[Dict] = Field(default=None, description="Session metadata (created_at, last_active, query_count).")
    restored_from_db: bool      = Field(default=False, description="True if session was restored from PostgreSQL.")


class SessionDeleteResponse(BaseModel):
    session_id: str = Field(...)
    message:    str = Field(default="Session deleted successfully.")


class SessionClearResponse(BaseModel):
    session_id: str = Field(...)
    message:    str = Field(default="Session history cleared successfully.")


class ConversationSummary(BaseModel):
    conversation_id: str
    title:           Optional[str] = None
    message_count:   int           = 0
    created_at:      Optional[str] = None
    last_message_at: Optional[str] = None
    is_archived:     bool          = False


class ConversationListResponse(BaseModel):
    conversations: List[ConversationSummary] = []
    total:         int                       = 0


# ==========================================
# Routes
# ==========================================

@router.post(
    "/session",
    response_model=SessionCreateResponse,
    summary="Create Session",
    description="Create a new chat session. Returns a session_id to pass in future /query requests.",
)
async def create_session(
    current_user: Optional[dict] = Depends(get_optional_user),
) -> SessionCreateResponse:
    """Create a new empty session in Redis (and PostgreSQL if user is authenticated)."""
    from src.memory.memory_manager import MemoryManager

    user_id    = current_user["user_id"] if current_user else None
    memory     = MemoryManager()
    session_id = memory.create_session(user_id=user_id)

    logger.info(f"POST /session | new session created | session_id={session_id} | user_id={user_id}")
    return SessionCreateResponse(session_id=session_id)


@router.get(
    "/session",
    response_model=ConversationListResponse,
    summary="List My Conversations",
    description="List all past conversations for the authenticated user (requires login).",
)
async def list_conversations(
    current_user: dict = Depends(get_current_user),
) -> ConversationListResponse:
    """Return all past conversations for the current user from PostgreSQL."""
    from src.memory.memory_manager import MemoryManager

    memory        = MemoryManager()
    conversations = memory.get_user_conversations(current_user["user_id"])

    logger.info(
        f"GET /session | user_id={current_user['user_id']} | "
        f"conversations={len(conversations)}"
    )
    return ConversationListResponse(
        conversations=[ConversationSummary(**c) for c in conversations],
        total=len(conversations),
    )


@router.get(
    "/session/{session_id}",
    response_model=SessionInfoResponse,
    summary="Get Session Info",
    description="Get session metadata and full chat history.",
)
async def get_session(session_id: str) -> SessionInfoResponse:
    """Load session history and metadata from Redis (restores from PostgreSQL if expired)."""

    from src.memory.memory_manager import MemoryManager

    memory  = MemoryManager()
    exists  = memory.session_exists(session_id)
    restored_from_db = False

    if not exists:
        # Try PostgreSQL restore before returning not-found
        history = memory.get_history(session_id)  # get_history handles restore internally
        if history:
            exists           = True
            restored_from_db = True
            meta             = None
        else:
            logger.warning(f"GET /session | not found | session_id={session_id}")
            return SessionInfoResponse(
                session_id=session_id,
                exists=False,
                history=[],
                meta=None,
            )
    else:
        history = memory.get_history(session_id)
        meta    = memory.get_meta(session_id)

    logger.info(
        f"GET /session | session_id={session_id} | turns={len(history)} | "
        f"restored_from_db={restored_from_db}"
    )

    return SessionInfoResponse(
        session_id=session_id,
        exists=True,
        history=history,
        meta=meta if not restored_from_db else None,
        restored_from_db=restored_from_db,
    )


@router.delete(
    "/session/{session_id}",
    response_model=SessionDeleteResponse,
    summary="Delete Session",
    description="Permanently delete a session and all its chat history from Redis.",
)
async def delete_session(session_id: str) -> SessionDeleteResponse:
    """Delete session from Redis."""

    from src.memory.memory_manager import MemoryManager

    memory = MemoryManager()

    if not memory.session_exists(session_id):
        raise HTTPException(
            status_code=404,
            detail=f"Session '{session_id}' not found or already expired."
        )

    memory.delete_session(session_id)

    logger.info(f"DELETE /session | session_id={session_id}")

    return SessionDeleteResponse(session_id=session_id)


@router.post(
    "/session/{session_id}/clear",
    response_model=SessionClearResponse,
    summary="Clear Session History",
    description="Clear chat history for a session without deleting the session itself. Useful for starting a new topic.",
)
async def clear_session(session_id: str) -> SessionClearResponse:
    """Clear chat history but keep session alive in Redis."""

    from src.memory.memory_manager import MemoryManager

    memory = MemoryManager()

    if not memory.session_exists(session_id):
        raise HTTPException(
            status_code=404,
            detail=f"Session '{session_id}' not found or already expired."
        )

    memory.clear_history(session_id)

    logger.info(f"POST /session/clear | session_id={session_id}")

    return SessionClearResponse(session_id=session_id)
