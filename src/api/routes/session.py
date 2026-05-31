"""
Session routes — manage Redis-backed chat memory sessions.

Routes:
    POST   /session               — create a new session
    GET    /session/{session_id}  — get session info + history
    DELETE /session/{session_id}  — delete a session (clear memory)
    POST   /session/{session_id}/clear — clear history but keep session alive
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict

from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ==========================================
# Response Models
# ==========================================

class SessionCreateResponse(BaseModel):
    session_id: str = Field(..., description="Newly created session ID. Pass this in future /query requests.")
    message: str = Field(default="Session created successfully.")


class SessionInfoResponse(BaseModel):
    session_id: str = Field(..., description="Session ID.")
    exists: bool = Field(..., description="True if session is alive in Redis.")
    history: List[Dict] = Field(default=[], description="Full chat history for this session.")
    meta: Optional[Dict] = Field(default=None, description="Session metadata (created_at, last_active, query_count).")


class SessionDeleteResponse(BaseModel):
    session_id: str = Field(...)
    message: str = Field(default="Session deleted successfully.")


class SessionClearResponse(BaseModel):
    session_id: str = Field(...)
    message: str = Field(default="Session history cleared successfully.")


# ==========================================
# Routes
# ==========================================

@router.post(
    "/session",
    response_model=SessionCreateResponse,
    summary="Create Session",
    description="Create a new chat session. Returns a session_id to pass in future /query requests.",
)
async def create_session() -> SessionCreateResponse:
    """Create a new empty session in Redis."""

    from src.memory.memory_manager import MemoryManager

    memory = MemoryManager()
    session_id = memory.create_session()

    logger.info(f"POST /session | new session created | session_id={session_id}")

    return SessionCreateResponse(session_id=session_id)


@router.get(
    "/session/{session_id}",
    response_model=SessionInfoResponse,
    summary="Get Session Info",
    description="Get session metadata and full chat history.",
)
async def get_session(session_id: str) -> SessionInfoResponse:
    """Load session history and metadata from Redis."""

    from src.memory.memory_manager import MemoryManager

    memory = MemoryManager()
    exists = memory.session_exists(session_id)

    if not exists:
        logger.warning(f"GET /session | not found | session_id={session_id}")
        return SessionInfoResponse(
            session_id=session_id,
            exists=False,
            history=[],
            meta=None,
        )

    history = memory.get_history(session_id)
    meta = memory.get_meta(session_id)

    logger.info(
        f"GET /session | session_id={session_id} | turns={len(history)}"
    )

    return SessionInfoResponse(
        session_id=session_id,
        exists=True,
        history=history,
        meta=meta,
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