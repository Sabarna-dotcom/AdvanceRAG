"""
Test script for the retrieval layer.
Tests each retrieval component step by step.

Run with:
    python -m tests.test_retrieval

or:

    python tests/test_retrieval.py
"""

import sys
import traceback


# =========================================================
# Helpers
# =========================================================

def print_header(title: str):
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)


def print_result(label: str, value):
    print(f" ✓ {label}: {value}")


def print_fail(label: str, error):
    print(f" ✗ {label}: {error}")


def print_chunk(idx: int, chunk: dict):

    text = chunk.get("text", "")[:120].replace("\n", " ")
    score = (
        chunk.get("rerank_score")
        or chunk.get("rrf_score")
        or chunk.get("score", 0)
    )

    source = (
        chunk.get("metadata", {})
        .get("source_name", "unknown")
    )

    page = (
        chunk.get("metadata", {})
        .get("page_number")
    )

    print(f" [{idx}] score={score:.4f} | {source} p.{page}")
    print(f"      {text}...")


# =========================================================
# Test Queries
# =========================================================

SIMPLE_QUERY = "What is photosynthesis?"
COMPARISON_QUERY = "Compare C3 and C4 photosynthesis"
COMPLEX_QUERY = "How do C3 plants adapt to drought stress?"


# =========================================================
# Test 1: Vector Retriever
# =========================================================

def test_vector_retriever():

    print_header("TEST 1: VectorRetriever")

    try:

        from src.retrieval.vector_retriever import VectorRetriever

        retriever = VectorRetriever()

        print_result("Initialized", "VectorRetriever")

        # Test PDF collection
        print("\n → Querying PDF collection...")

        results = retriever.retrieve_pdf(
            query=SIMPLE_QUERY,
            top_k=3
        )

        print_result("PDF results", len(results))

        for i, r in enumerate(results, 1):
            print_chunk(i, r)

        # Test Audio collection
        print("\n → Querying Audio collection...")

        results_audio = retriever.retrieve_audio(
            query="HTML website CSS",
            top_k=3
        )

        print_result(
            "Audio results",
            len(results_audio)
        )

        for i, r in enumerate(results_audio, 1):
            print_chunk(i, r)

        # Test both collections
        print("\n → Querying both collections...")

        results_both = retriever.retrieve(
            query=SIMPLE_QUERY,
            top_k=5
        )

        print_result(
            "Both collections results",
            len(results_both)
        )

        print("\n ✅ VectorRetriever PASSED")

        return True

    except Exception as e:

        print_fail("VectorRetriever FAILED", e)

        traceback.print_exc()

        return False


# =========================================================
# Test 2: Query Processor
# =========================================================

def test_query_processor():

    print_header("TEST 2: QueryProcessor")

    try:

        from src.retrieval.query_processor import QueryProcessor

        processor = QueryProcessor()

        print_result("Initialized", "QueryProcessor")

        # Test clean
        raw = "  What is photosynthesis?  "

        cleaned = processor.clean(raw)

        print_result(
            "Cleaned query",
            f"'{cleaned}'"
        )

        assert cleaned == "What is photosynthesis?", "Clean failed"

        # Test with no history
        result = processor.process(SIMPLE_QUERY)

        print_result(
            "Process (no history)",
            result[:60]
        )

        # Test with history
        history = [
            {
                "role": "user",
                "content": "What is biology?"
            },
            {
                "role": "assistant",
                "content": "Biology is the study of living things."
            }
        ]

        result_with_history = processor.process(
            query="Can you explain more?",
            chat_history=history
        )

        print_result(
            "Process (with history)",
            result_with_history[:80]
        )

        assert "[Context]" in result_with_history or "[context]" in result_with_history.lower(), "History injection failed"

        print("\n ✅ QueryProcessor PASSED")

        return True

    except Exception as e:

        print_fail("QueryProcessor FAILED", e)

        traceback.print_exc()

        return False


# =========================================================
# Test 3: Hybrid Retriever
# =========================================================

def test_hybrid_retriever():

    print_header("TEST 3: HybridRetriever")

    try:

        from src.retrieval.hybrid_retriever import HybridRetriever

        retriever = HybridRetriever()

        print_result("Initialized", "HybridRetriever")

        print("\n → Running hybrid retrieval...")

        results = retriever.retrieve(
            query=COMPARISON_QUERY,
            top_k=5
        )

        print_result(
            "Hybrid results",
            len(results)
        )

        for i, r in enumerate(results, 1):
            print_chunk(i, r)

        # Verify RRF scores exist
        has_rrf = any(
            "rrf_score" in r
            for r in results
        )

        print_result(
            "RRF scores present",
            has_rrf
        )

        print("\n ✅ HybridRetriever PASSED")

        return True

    except Exception as e:

        print_fail("HybridRetriever FAILED", e)

        traceback.print_exc()

        return False


# =========================================================
# Test 4: Adaptive Retriever
# =========================================================

def test_adaptive_retriever():

    print_header("TEST 4: AdaptiveRetriever")

    try:

        from src.retrieval.adaptive_retriever import AdaptiveRetriever

        retriever = AdaptiveRetriever()

        print_result("Initialized", "AdaptiveRetriever")

        # Test intent detection
        test_cases = [
            ("What is photosynthesis?", "definition"),
            ("Compare C3 and C4 plants", "comparison"),
            ("How does the Calvin cycle work?", "explanation"),
            ("Who discovered photosynthesis?", "simple_fact"),
        ]

        print("\n → Testing intent detection...")

        for query, expected in test_cases:

            detected = retriever.detect_intent(query)

            top_k = retriever.determine_top_k(query)

            status = "✓" if detected == expected else "✗"

            print(
                f"{status} '{query[:40]}' "
                f"→ intent={detected} top_k={top_k}"
            )

        # Test full adaptive retrieval
        print(
            "\n → Running adaptive retrieval "
            "(comparison query)..."
        )

        results = retriever.retrieve(
            query=COMPARISON_QUERY,
            collection="pdf"
        )

        print_result(
            "Adaptive results",
            len(results)
        )

        for i, r in enumerate(results[:3], 1):
            print_chunk(i, r)

        print("\n ✅ AdaptiveRetriever PASSED")

        return True

    except Exception as e:

        print_fail("AdaptiveRetriever FAILED", e)

        traceback.print_exc()

        return False


# =========================================================
# Test 5: Query Decomposer
# =========================================================

def test_query_decomposer():

    print_header(
        "TEST 5: QueryDecomposer "
        "(uses Ollama LLM)"
    )

    try:

        from src.retrieval.query_decomposer import QueryDecomposer

        decomposer = QueryDecomposer()

        print_result("Initialized", "QueryDecomposer")

        print(
            f"\n → Decomposing: "
            f"'{COMPLEX_QUERY}'"
        )

        sub_questions = decomposer.decompose(COMPLEX_QUERY)

        print_result(
            "Sub-questions generated",
            len(sub_questions)
        )

        for i, q in enumerate(sub_questions, 1):
            print(f"   {i}. {q}")

        assert (
            len(sub_questions) >= 1
        ), "Should return at least original query"

        print("\n ✅ QueryDecomposer PASSED")

        return True

    except Exception as e:

        print_fail("QueryDecomposer FAILED", e)

        traceback.print_exc()

        return False


# =========================================================
# Test 6: HyDE Retriever
# =========================================================

def test_hyde_retriever():

    print_header(
        "TEST 6: HyDERetriever "
        "(uses Ollama LLM)"
    )

    try:

        from src.retrieval.hyde_retriever import HyDERetriever

        retriever = HyDERetriever()

        print_result("Initialized", "HyDERetriever")

        print(
            f"\n → Running HyDE for: "
            f"'{SIMPLE_QUERY}'"
        )

        results = retriever.retrieve(
            query=SIMPLE_QUERY,
            top_k=3,
            collection="pdf"
        )

        print_result(
            "HyDE results",
            len(results)
        )

        for i, r in enumerate(results, 1):
            print_chunk(i, r)

        # Verify retrieval method tag
        has_tag = all(
            r.get("retrieval_method") == "hyde"
            for r in results
        )

        print_result(
            "Tagged as hyde",
            has_tag
        )

        print("\n ✅ HyDERetriever PASSED")

        return True

    except Exception as e:

        print_fail("HyDERetriever FAILED", e)

        traceback.print_exc()

        return False


# =========================================================
# Test 7: Fusion Retriever
# =========================================================

def test_fusion_retriever():

    print_header(
        "TEST 7: FusionRetriever "
        "(uses Ollama LLM)"
    )

    try:

        from src.retrieval.fusion_retriever import FusionRetriever

        retriever = FusionRetriever()

        print_result("Initialized", "FusionRetriever")

        print(
            f"\n → Running Fusion for: "
            f"'{COMPARISON_QUERY}'"
        )

        results = retriever.retrieve(
            query=COMPARISON_QUERY,
            top_k=5,
            collection="pdf"
        )

        print_result(
            "Fusion results",
            len(results)
        )

        for i, r in enumerate(results[:3], 1):
            print_chunk(i, r)

        print("\n ✅ FusionRetriever PASSED")

        return True

    except Exception as e:

        print_fail("FusionRetriever FAILED", e)

        traceback.print_exc()

        return False


# =========================================================
# Test 8: Reranker
# =========================================================

def test_reranker():

    print_header(
        "TEST 8: Reranker (flashrank)"
    )

    try:

        from src.retrieval.vector_retriever import VectorRetriever
        from src.retrieval.reranker import Reranker

        # Get some chunks first
        retriever = VectorRetriever()

        chunks = retriever.retrieve(
            query=SIMPLE_QUERY,
            top_k=10,
            collection="pdf"
        )

        print_result(
            "Chunks to rerank",
            len(chunks)
        )

        # Rerank
        reranker = Reranker()

        print_result(
            "Initialized",
            "Reranker (flashrank)"
        )

        print(
            f"\n → Reranking "
            f"{len(chunks)} chunks..."
        )

        reranked = reranker.rerank(
            query=SIMPLE_QUERY,
            chunks=chunks,
            top_k=5
        )

        print_result(
            "Reranked results",
            len(reranked)
        )

        for i, r in enumerate(reranked, 1):
            print_chunk(i, r)

        # Verify rerank scores
        has_scores = all(
            "rerank_score" in r
            for r in reranked
        )

        print_result(
            "Rerank scores present",
            has_scores
        )

        # Verify sorted
        scores = [
            r["rerank_score"]
            for r in reranked
        ]

        is_sorted = all(
            scores[i] >= scores[i + 1]
            for i in range(len(scores) - 1)
        )

        print_result(
            "Results sorted by score",
            is_sorted
        )

        print("\n ✅ Reranker PASSED")

        return True

    except Exception as e:

        print_fail("Reranker FAILED", e)

        traceback.print_exc()

        return False


# =========================================================
# Test 9: Full Retrieval Manager
# =========================================================

def test_retrieval_manager():

    print_header(
        "TEST 9: RetrievalManager "
        "(Full Pipeline)"
    )

    try:

        from src.retrieval.retrieval_manager import RetrievalManager

        manager = RetrievalManager()

        print_result(
            "Initialized",
            "RetrievalManager"
        )

        # Test 1: Simple query
        print(
            f"\n → Simple query: "
            f"'{SIMPLE_QUERY}'"
        )

        results = manager.retrieve(
            query=SIMPLE_QUERY,
            collection="pdf"
        )

        print_result(
            "Final results",
            len(results)
        )

        for i, r in enumerate(results, 1):
            print_chunk(i, r)

        # Test 2: Complex query with chat history
        print(
            f"\n → Complex query with history: "
            f"'{COMPLEX_QUERY}'"
        )

        history = [
            {
                "role": "user",
                "content": "Tell me about plants"
            },
            {
                "role": "assistant",
                "content": (
                    "Plants are organisms "
                    "that photosynthesize."
                )
            }
        ]

        results2 = manager.retrieve(
            query=COMPLEX_QUERY,
            chat_history=history,
            collection="pdf"
        )

        print_result(
            "Final results (with history)",
            len(results2)
        )

        # Test 3: With decomposition
        print(
            f"\n → Retrieval with decomposition: "
            f"'{COMPARISON_QUERY}'"
        )

        results3 = manager.retrieve_with_decomposition(
            query=COMPARISON_QUERY,
            collection="pdf"
        )

        print_result(
            "Final results (decomposed)",
            len(results3)
        )

        print("\n ✅ RetrievalManager PASSED")

        return True

    except Exception as e:

        print_fail("RetrievalManager FAILED", e)

        traceback.print_exc()

        return False


# =========================================================
# Main Runner
# =========================================================

def main():

    print("\n" + "🔍 " * 20)
    print(" RETRIEVAL LAYER TEST SUITE")
    print("🔍 " * 20)

    results = {}

    # Run all tests
    # Tests 1-4 are fast (no LLM calls)
    # Tests 5-7 are slower (use Ollama LLM)

    results["1. VectorRetriever"] = test_vector_retriever()
    results["2. QueryProcessor"] = test_query_processor()
    results["3. HybridRetriever"] = test_hybrid_retriever()
    results["4. AdaptiveRetriever"] = test_adaptive_retriever()
    results["5. QueryDecomposer"] = test_query_decomposer()
    results["6. HyDERetriever"] = test_hyde_retriever()
    results["7. FusionRetriever"] = test_fusion_retriever()
    results["8. Reranker"] = test_reranker()
    results["9. RetrievalManager"] = test_retrieval_manager()

    # Summary
    print_header("FINAL RESULTS")

    passed = 0
    failed = 0

    for test_name, result in results.items():

        status = "✅ PASS" if result else "❌ FAIL"

        print(f" {status} {test_name}")

        if result:
            passed += 1
        else:
            failed += 1

    print(
        f"\n Total: {passed} passed, "
        f"{failed} failed"
    )

    if failed == 0:
        print(
            "\n 🎉 ALL TESTS PASSED "
            "— Retrieval layer is working!"
        )
    else:
        print(
            f"\n ⚠️ {failed} test(s) failed "
            "— check errors above"
        )

    return failed == 0


if __name__ == "__main__":

    success = main()

    sys.exit(0 if success else 1)