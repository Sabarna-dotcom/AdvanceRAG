"""
Query route — the main RAG endpoint.
POST /query — takes a question and returns an answer with citations.
"""

import time
from typing import Optional

from fastapi import APIRouter, Depends
from src.api.models.request import QueryRequest
from src.api.models.response import QueryResponse, CitedSource, ReflectionResult
from src.auth.dependencies import get_optional_user
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
async def query(
    request: QueryRequest,
    current_user: Optional[dict] = Depends(get_optional_user),
) -> QueryResponse:
    """
    Full RAG pipeline:
    1. Load or create session memory from Redis
    2. Retrieve relevant chunks from Qdrant
    3. Build context with citations
    4. Generate answer via Ollama LLM
    5. Self-reflection + corrective loop (if enabled)
    6. Save exchange to Redis + PostgreSQL
    7. Save query log to PostgreSQL
    8. Return structured answer with cited sources + session_id
    """
    start_time = time.time()
    user_id    = current_user["user_id"] if current_user else None

    logger.info(
        f"POST /query | query='{request.query[:80]}' | "
        f"collection={request.collection} | top_k={request.top_k} | "
        f"session_id={request.session_id} | user_id={user_id}"
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
        session_id = memory.create_session(user_id=user_id)
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
    # Step 2: Cache check — skip pipeline on HIT
    # ------------------------------------------
    from src.memory.cache_manager import CacheManager

    cache = CacheManager()
    cached_result = None
    query_embedding_for_cache = None

    # 2a: Exact match
    cached_result = cache.get_query_result(
        query=request.query,
        collection=request.collection,
    )

    # 2b: Semantic match (if no exact hit) — need embedding of the query
    if cached_result is None:
        try:
            from src.embeddings.embedding_model import OllamaEmbeddingModel
            _emb_model = OllamaEmbeddingModel()
            _embs = _emb_model.embed([request.query])
            if _embs:
                query_embedding_for_cache = _embs[0]
                cached_result = cache.get_semantic_query_result(
                    query_embedding=query_embedding_for_cache,
                    collection=request.collection,
                )
        except Exception as _ce:
            logger.warning(f"POST /query | cache embedding lookup failed: {_ce}")

    if cached_result is not None:
        logger.info(
            f"POST /query | CACHE HIT — skipping retrieval+generation | "
            f"session_id={session_id}"
        )
        result = cached_result
    else:
        # ------------------------------------------
        # Step 2c: Full pipeline — Retrieve + Generate
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

        # Store result in cache for future requests
        cache.set_query_result(
            query=request.query,
            collection=request.collection,
            result=result,
            query_embedding=query_embedding_for_cache,
        )

    # ------------------------------------------
    # Step 3: Save exchange to Redis + PostgreSQL
    # ------------------------------------------
    memory.append_exchange(
        session_id       = session_id,
        user_query       = request.query,
        assistant_answer = result["answer"],
        user_id          = user_id,
        sources          = result.get("cited_sources"),
    )

    # ------------------------------------------
    # Step 3b: Save query log to PostgreSQL (non-blocking)
    # ------------------------------------------
    try:
        from src.memory.postgres_memory import PostgresMemory
        pg = PostgresMemory()
        if pg.is_available:
            latency_ms = int((time.time() - start_time) * 1000)
            pg.save_query_log(
                conversation_id    = session_id,
                query              = request.query,
                user_id            = user_id,
                response           = result["answer"],
                retrieval_count    = len(result.get("cited_sources", [])),
                sources_used       = result.get("cited_sources"),
                latency_ms         = latency_ms,
                cache_hit          = result.get("cached", False),
            )
    except Exception as _qle:
        logger.warning(f"POST /query | query log save failed (non-critical): {_qle}")

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
        cached=result.get("cached", False),
        guardrail_warnings=result.get("guardrail_warnings") or None,
    )