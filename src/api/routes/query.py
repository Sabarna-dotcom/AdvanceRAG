"""
Query route — the main RAG endpoint.
POST /query — takes a question and returns an answer with citations.
"""

from fastapi import APIRouter
from src.api.models.request import QueryRequest
from src.api.models.response import QueryResponse, CitedSource, ReflectionResult
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post(
    "/query",
    response_model=QueryResponse,
    summary="Ask a Question",
    description=(
        "Send a question to the RAG system. "
        "Optionally filter by collection ('pdf' or 'audio') and pass a session_id for memory. "
        "If no session_id is provided, a new session is created automatically. "
        "If no collection is specified, both PDF and audio sources are searched."
    ),
)
async def query(request: QueryRequest) -> QueryResponse:
    """
    Full RAG pipeline:
    1. Load or create session memory from Redis
    2. Retrieve relevant chunks from Qdrant
    3. Build context with citations
    4. Generate answer via Ollama LLM
    5. Self-reflection + corrective loop (if enabled)
    6. Save exchange to Redis memory
    7. Return structured answer with cited sources + session_id
    """

    logger.info(
        f"POST /query | query='{request.query[:80]}' | "
        f"collection={request.collection} | top_k={request.top_k} | "
        f"session_id={request.session_id}"
    )

    # ------------------------------------------
    # Step 1: Memory — load or create session
    # ------------------------------------------
    from src.memory.memory_manager import MemoryManager

    memory = MemoryManager()

    # Use provided session_id or create a new one
    session_id = request.session_id
    if session_id and memory.session_exists(session_id):
        # Load history from Redis — client doesn't need to send it
        chat_history = memory.get_history(session_id)
        logger.info(
            f"POST /query | loaded memory | "
            f"session_id={session_id} | turns={len(chat_history)}"
        )
    else:
        # New session — create it
        session_id = memory.create_session()
        chat_history = []

        # If client sent manual chat_history (old-style), use it as seed
        if request.chat_history:
            chat_history = [
                {"role": turn.role, "content": turn.content}
                for turn in request.chat_history
            ]
            memory.save_history(session_id, chat_history)

        logger.info(f"POST /query | new session | session_id={session_id}")

    # ------------------------------------------
    # Step 2: Retrieve + Generate
    # ------------------------------------------
    from src.generation.generation_manager import GenerationManager
    from src.retrieval.retrieval_manager import RetrievalManager

    # Retrieve
    retriever = RetrievalManager()
    chunks = retriever.retrieve(
        query=request.query,
        chat_history=chat_history,
        collection=request.collection,
        top_k=request.top_k,
    )

    # Generate
    manager = GenerationManager(use_self_reflection=request.use_self_reflection)
    result = manager.generate(
        query=request.query,
        chunks=chunks,
        chat_history=chat_history,
        retriever=retriever,
        collection=request.collection,
    )

    # ------------------------------------------
    # Step 3: Save exchange to Redis memory
    # ------------------------------------------
    memory.append_exchange(
        session_id=session_id,
        user_query=request.query,
        assistant_answer=result["answer"],
    )

    # ------------------------------------------
    # Step 4: Build response
    # ------------------------------------------
    cited_sources = []
    for src in result.get("cited_sources", []):
        cited_sources.append(
            CitedSource(
                index=src.get("index"),
                source_type=src.get("source_type", "unknown"),
                title=src.get("title", "Unknown"),
                page=src.get("page"),
                start_time=src.get("start_time"),
                end_time=src.get("end_time"),
                preview=src.get("preview"),
            )
        )

    reflection = None
    raw_reflection = result.get("reflection")
    if raw_reflection:
        reflection = ReflectionResult(
            overall_confidence=raw_reflection.get("overall_confidence"),
            accuracy_confidence=raw_reflection.get("accuracy_confidence"),
            completeness_confidence=raw_reflection.get("completeness_confidence"),
            citation_confidence=raw_reflection.get("citation_confidence"),
            needs_more_retrieval=raw_reflection.get("needs_more_retrieval"),
            improvement_hint=raw_reflection.get("improvement_hint"),
            uncertainties=raw_reflection.get("uncertainties"),
        )

    logger.info(
        f"POST /query complete | has_answer={result['has_answer']} | "
        f"cited_sources={len(cited_sources)} | iterations={result.get('iterations', 1)} | "
        f"session_id={session_id}"
    )

    return QueryResponse(
        answer=result["answer"],
        cited_sources=cited_sources,
        cited_indices=result.get("cited_indices", []),
        has_answer=result["has_answer"],
        iterations=result.get("iterations", 1),
        reflection=reflection,
        session_id=session_id,
    )