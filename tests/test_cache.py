"""
Cache Manager test suite.

Run:
    python -m tests.test_cache
"""

import json
import sys

# =====================================================================
# Helpers
# =====================================================================

def section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def ok(msg):  print(f"  ✓  {msg}")
def fail(msg, exc=None):
    print(f"  ✗  {msg}")
    if exc:
        import traceback
        traceback.print_exc()

# =====================================================================
# TEST 1 — Init
# =====================================================================

section("TEST 1: CacheManager Init")
try:
    from src.memory.cache_manager import CacheManager
    cache = CacheManager()
    assert hasattr(cache, "client"), "client attribute missing"
    if cache.client is None:
        fail("Redis not reachable — is Redis running? (docker-compose up -d redis)")
        print("\n  Run:  docker-compose up -d redis")
        print("  Then retry this test.\n")
        sys.exit(1)
    ok(f"CacheManager initialized | ttl_query={cache.ttl_query}s | threshold={cache.threshold}")
except Exception as e:
    fail("CacheManager init FAILED", e)
    sys.exit(1)

# =====================================================================
# TEST 2 — Redis Ping
# =====================================================================

section("TEST 2: Redis Ping")
try:
    result = cache.client.ping()
    assert result is True
    ok("Redis ping: PONG")
except Exception as e:
    fail("Redis ping failed", e)
    sys.exit(1)

# =====================================================================
# TEST 3 — Embedding Cache
# =====================================================================

section("TEST 3: Embedding Cache (Layer 2)")
try:
    test_text = "photosynthesis is the process by which plants make food"
    dummy_emb = [0.1, 0.2, 0.3, 0.4, 0.5]

    # Should be miss first
    result = cache.get_embedding(test_text)
    assert result is None, f"Expected None, got {result}"
    ok("get_embedding: MISS (correct)")

    # Store it
    cache.set_embedding(test_text, dummy_emb)
    ok("set_embedding: stored")

    # Should hit now
    result = cache.get_embedding(test_text)
    assert result == dummy_emb, f"Expected {dummy_emb}, got {result}"
    ok("get_embedding: HIT (correct)")

    # Cleanup
    key = cache._EMB_PREFIX.format(cache._hash(test_text))
    cache.client.delete(key)
    ok("Cleanup: embedding key deleted")

except Exception as e:
    fail("Embedding cache test FAILED", e)

# =====================================================================
# TEST 4 — Query Result Cache (Layer 1 — exact match)
# =====================================================================

section("TEST 4: Query Result Cache (Layer 1 — Exact Match)")
try:
    test_query = "_test_query_cache_check_"
    test_collection = "pdf"
    dummy_result = {
        "answer": "This is a test answer.",
        "cited_sources": [],
        "has_answer": True,
        "iterations": 1,
    }

    # Miss first
    result = cache.get_query_result(test_query, test_collection)
    assert result is None, f"Expected None, got {result}"
    ok("get_query_result: MISS (correct)")

    # Store
    cache.set_query_result(test_query, test_collection, dummy_result)
    ok("set_query_result: stored")

    # Hit
    result = cache.get_query_result(test_query, test_collection)
    assert result is not None, "Expected cached result, got None"
    assert result["answer"] == dummy_result["answer"]
    ok(f"get_query_result: HIT (correct) — answer='{result['answer']}'")

    # Case insensitive — uppercase query should hit same cache
    result2 = cache.get_query_result(test_query.upper(), test_collection)
    assert result2 is not None, "Case-insensitive lookup failed"
    ok("get_query_result: case-insensitive HIT (correct)")

    # Different collection = different key
    result3 = cache.get_query_result(test_query, "audio")
    assert result3 is None, "Different collection should be cache MISS"
    ok("get_query_result: different collection = MISS (correct)")

except Exception as e:
    fail("Query cache test FAILED", e)

# =====================================================================
# TEST 5 — Cache Invalidation
# =====================================================================

section("TEST 5: Cache Invalidation")
try:
    # Invalidate the test query
    cache.invalidate_query(test_query, test_collection)
    ok("invalidate_query: called")

    # Should be miss now
    result = cache.get_query_result(test_query, test_collection)
    assert result is None, f"Expected None after invalidation, got {result}"
    ok("get_query_result after invalidation: MISS (correct)")

except Exception as e:
    fail("Cache invalidation test FAILED", e)

# =====================================================================
# TEST 6 — Semantic Cache (Layer 3)
# =====================================================================

section("TEST 6: Semantic Cache (Layer 3)")
try:
    query1 = "_semantic_test_query_A_"
    query2 = "_semantic_test_query_B_"
    collection = "pdf"

    # Two very similar embeddings (cosine similarity will be ~1.0)
    emb1 = [1.0, 0.0, 0.0, 0.0]
    emb2 = [0.99, 0.01, 0.0, 0.0]   # very close to emb1

    dummy_result = {"answer": "Semantic hit answer", "has_answer": True, "cited_sources": []}

    # Store query1 result with its embedding
    cache.set_query_result(query1, collection, dummy_result, query_embedding=emb1)
    ok(f"Stored query1 result with embedding")

    # Look up query2 using emb2 — should semantically hit query1's result
    hit = cache.get_semantic_query_result(emb2, collection)
    if hit is not None:
        ok(f"Semantic cache HIT (correct) — answer='{hit['answer']}'")
    else:
        fail("Semantic cache MISS (unexpected) — similarity should be >= 0.95")

    # Cleanup
    cache.invalidate_query(query1, collection)
    ok("Cleanup: semantic test keys deleted")

except Exception as e:
    fail("Semantic cache test FAILED", e)

# =====================================================================
# TEST 7 — Stats
# =====================================================================

section("TEST 7: Cache Stats")
try:
    stats = cache.get_stats()
    assert stats["redis_reachable"] is True
    assert isinstance(stats["query_cache_count"], int)
    assert isinstance(stats["embedding_cache_count"], int)
    assert isinstance(stats["semantic_index_count"], int)
    ok(f"redis_reachable       : {stats['redis_reachable']}")
    ok(f"query_cache_count     : {stats['query_cache_count']}")
    ok(f"embedding_cache_count : {stats['embedding_cache_count']}")
    ok(f"semantic_index_count  : {stats['semantic_index_count']}")
    ok(f"ttl_query (hours)     : {stats['ttl_query_seconds'] // 3600}h")
    ok(f"ttl_embedding (days)  : {stats['ttl_embedding_seconds'] // 86400}d")
    ok(f"similarity_threshold  : {stats['similarity_threshold']}")
except Exception as e:
    fail("Stats test FAILED", e)

# =====================================================================
# TEST 8 — Flush All Cache
# =====================================================================

section("TEST 8: Flush All Cache")
try:
    # Store something first
    cache.set_query_result("_flush_test_", "pdf", {"answer": "temp", "has_answer": True, "cited_sources": []})
    stats_before = cache.get_stats()
    ok(f"Before flush — query_cache_count: {stats_before['query_cache_count']}")

    deleted = cache.flush_all_cache()
    ok(f"flush_all_cache: deleted {deleted} keys")

    stats_after = cache.get_stats()
    assert stats_after["query_cache_count"] == 0, f"Expected 0, got {stats_after['query_cache_count']}"
    assert stats_after["semantic_index_count"] == 0
    ok(f"After flush — query_cache_count: {stats_after['query_cache_count']} (correct)")

except Exception as e:
    fail("Flush test FAILED", e)

# =====================================================================
# SUMMARY
# =====================================================================

print(f"\n{'='*60}")
print("  ALL CACHE TESTS PASSED ✅")
print(f"{'='*60}\n")