"""
Response schemas for the RAG API.
All outgoing response bodies are defined here via Pydantic.
"""

from typing import List, Optional, Any
from pydantic import BaseModel, Field


class CitedSource(BaseModel):
    """A single cited source in the answer."""

    index: int = Field(
        ...,
        description="Source number as referenced in the answer e.g. [Source 1]."
    )

    source_type: str = Field(
        ...,
        description="'pdf' or 'audio'."
    )

    title: str = Field(
        ...,
        description="PDF filename or audio lecture title."
    )

    page: Optional[int] = Field(
        default=None,
        description="Page number (PDF only)."
    )

    start_time: Optional[str] = Field(
        default=None,
        description="Start timestamp MM:SS (audio only)."
    )

    end_time: Optional[str] = Field(
        default=None,
        description="End timestamp MM:SS (audio only)."
    )

    preview: Optional[str] = Field(
        default=None,
        description="First 120 chars of the source chunk."
    )


class ReflectionResult(BaseModel):
    """Self-reflection scores from the generation layer."""

    overall_confidence: Optional[float] = Field(
        default=None,
        description="0.0 - 1.0 confidence score."
    )

    accuracy_confidence: Optional[float] = None
    completeness_confidence: Optional[float] = None
    citation_confidence: Optional[float] = None

    needs_more_retrieval: Optional[bool] = None
    improvement_hint: Optional[str] = None
    uncertainties: Optional[List[str]] = None


class QueryResponse(BaseModel):
    """
    Response body for POST /query.

    Example:
    {
        "answer": "Biotechnology is the use of biological systems...[Source 1]",
        "cited_sources": [
            {
                "index": 1,
                "source_type": "pdf",
                "title": "10. Biotechnology and its Application.pdf",
                "page": null,
                "start_time": null,
                "end_time": null,
                "preview": "Biotechnology essentially deals with..."
            }
        ],
        "has_answer": true,
        "iterations": 1,
        "reflection": {
            "overall_confidence": 0.87
        }
    }
    """

    answer: str = Field(
        ...,
        description="The generated answer with inline [Source N] citations."
    )

    cited_sources: List[CitedSource] = Field(
        default=[],
        description="Full citation details for each source referenced."
    )

    cited_indices: List[int] = Field(
        default=[],
        description="Source numbers referenced in the answer."
    )

    has_answer: bool = Field(
        ...,
        description="False if the system could not find enough information."
    )

    iterations: int = Field(
        default=1,
        description="How many generation iterations were run (self-reflection loop)."
    )

    reflection: Optional[ReflectionResult] = Field(
        default=None,
        description="Self reflection scores if enabled."
    )

    session_id: Optional[str] = Field(
        default=None,
        description="Session ID for continuing the conversation. Pass this back in the next request."
    )

    cached: Optional[bool] = Field(
        default=False,
        description="True if this response was served from cache."
    )

    guardrail_warnings: Optional[List[str]] = Field(
        default=None,
        description="Output guardrail warnings e.g. possible hallucination, invalid citations."
    )


class HealthResponse(BaseModel):
    """Response body for GET /health."""

    status: str = Field(
        ...,
        description="'ok' or 'degraded'."
    )

    qdrant: bool = Field(
        ...,
        description="True if Qdrant is reachable."
    )

    ollama: bool = Field(
        ...,
        description="True if Ollama is reachable."
    )

    details: Optional[Any] = Field(
        default=None,
        description="Extra info or error messages."
    )


class ErrorResponse(BaseModel):
    """Standard error response body."""

    error: str = Field(
        ...,
        description="Short error type."
    )

    message: str = Field(
        ...,
        description="Human-readable error description."
    )

    details: Optional[str] = Field(
        default=None,
        description="Technical details for debugging."
    )