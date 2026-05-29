"""
Request schemas for the RAG API.
All incoming request bodies are validated here via Pydantic.
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class ChatTurn(BaseModel):
    """A single turn in a conversation."""

    role: Literal["user", "assistant"] = Field(
        ...,
        description="Who sent this message - 'user' or 'assistant'."
    )

    content: str = Field(
        ...,
        description="The message text."
    )


class QueryRequest(BaseModel):
    """
    Request body for POST /query.

    Example:
    {
        "query": "What is biotechnology?",
        "collection": "pdf",        # optional -> "pdf", "audio", or omit for both
        "chat_history": [           # optional
            {"role": "user", "content": "What is biology?"},
            {"role": "assistant", "content": "Biology is the study of life."}
        ],
        "top_k": 10                 # optional
    }
    """

    query: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The user's question."
    )

    collection: Optional[Literal["pdf", "audio"]] = Field(
        default=None,
        description="Which collection to search. Omit to search both PDF and audio."
    )

    chat_history: Optional[List[ChatTurn]] = Field(
        default=None,
        description="Previous conversation turns for follow-up question support."
    )

    top_k: Optional[int] = Field(
        default=10,
        ge=1,
        le=50,
        description="Number of chunks to retrieve. Default is 10."
    )

    use_self_reflection: Optional[bool] = Field(
        default=True,
        description="Whether to run self-reflection after generation. Set false for faster responses."
    )