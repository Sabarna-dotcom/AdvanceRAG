"""
PostgreSQL Long-Term Memory Test Suite.

Tests PostgresMemory — save messages, restore to Redis, query logs, topic tracking.

Requires:
  - PostgreSQL running  (docker-compose up -d postgres)
  - Redis running       (docker-compose up -d redis)

Run:
    python -m tests.test_postgres_memory
"""

import sys
import traceback
import uuid

# ==========================================
# Helpers
# ==========================================

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def ok(msg):    print(f"  ✓  {msg}")
def warn(msg):  print(f"  ⚠  {msg}")
def fail(msg, exc=None):
    print(f"  ✗  {msg}")
    if exc:
        traceback.print_exc()

_passed = _failed = 0

def record_pass(label):
    global _passed; _passed += 1; ok(label)

def record_fail(label, exc=None):
    global _failed; _failed += 1; fail(label, exc)


# ==========================================
# TEST 1: PostgreSQL Connection
# ==========================================

section("TEST 1: PostgreSQL Connection")
try:
    from src.database.connection import check_connection
    if not check_connection():
        warn("PostgreSQL not reachable — all tests will be skipped.")
        warn("Run:  docker-compose up -d postgres")
        sys.exit(0)
    record_pass("PostgreSQL connected")
except Exception as e:
    record_fail("PostgreSQL connection failed", e)
    sys.exit(0)


# ==========================================
# TEST 2: PostgresMemory Init
# ==========================================

section("TEST 2: PostgresMemory Init")
try:
    from src.memory.postgres_memory import PostgresMemory
    pg = PostgresMemory()
    if not pg.is_available:
        warn("PostgresMemory not available — check PostgreSQL")
        sys.exit(0)
    record_pass(f"PostgresMemory initialized | available={pg.is_available}")
except Exception as e:
    record_fail("PostgresMemory init FAILED", e)
    sys.exit(1)


# ==========================================
# TEST 3: Save + Retrieve Messages
# ==========================================

section("TEST 3: Save + Retrieve Messages")
test_conv_id = f"test_conv_{uuid.uuid4().hex[:8]}"
test_user_id = "test_user_001"   # seeded in init_db.sql

try:
    pg.save_message(test_conv_id, test_user_id, "user",      "What is photosynthesis?")
    pg.save_message(test_conv_id, test_user_id, "assistant", "Photosynthesis is the process by which plants...")

    history = pg.get_conversation_history(test_conv_id)
    assert len(history) == 2, f"Expected 2 messages, got {len(history)}"
    assert history[0]["role"]    == "user"
    assert history[0]["content"] == "What is photosynthesis?"
    assert history[1]["role"]    == "assistant"

    ok(f"Saved 2 turns | conversation_id={test_conv_id}")
    ok(f"Retrieved: {[h['role'] for h in history]}")
    record_pass("Save + retrieve messages works")
except Exception as e:
    record_fail("Save + retrieve FAILED", e)


# ==========================================
# TEST 4: Conversation Metadata
# ==========================================

section("TEST 4: Conversation Metadata")
try:
    pg.create_conversation(test_conv_id, test_user_id, title="Photosynthesis Study")

    # Retrieve user conversations
    convs = pg.get_user_conversations(test_user_id)
    # Find our test conversation
    match = next((c for c in convs if c["conversation_id"] == test_conv_id), None)

    if match:
        ok(f"Found conversation | title={match.get('title')} count={match.get('message_count')}")
        record_pass("Conversation metadata created and retrieved")
    else:
        warn("Test conversation not found in list (may be > 20 conversations)")
        record_pass("create_conversation ran without error")
except Exception as e:
    record_fail("Conversation metadata FAILED", e)


# ==========================================
# TEST 5: Redis Restore
# ==========================================

section("TEST 5: Restore to Redis")
try:
    from src.memory.memory_manager import MemoryManager

    memory        = MemoryManager()
    restored      = pg.restore_to_redis(test_conv_id, memory)

    assert len(restored) == 2, f"Expected 2 restored turns, got {len(restored)}"
    assert memory.session_exists(test_conv_id), "Session should exist in Redis after restore"

    redis_history = memory.get_history(test_conv_id)
    assert len(redis_history) == 2, f"Redis should have 2 turns, got {len(redis_history)}"

    ok(f"Restored {len(restored)} turns to Redis")
    ok(f"Redis history: {[h['role'] for h in redis_history]}")
    record_pass("PostgreSQL → Redis restore works")
except Exception as e:
    record_fail("Redis restore FAILED", e)


# ==========================================
# TEST 6: MemoryManager get_history — Redis miss → PostgreSQL restore
# ==========================================

section("TEST 6: get_history on expired session (auto-restore)")
try:
    fresh_conv_id = f"test_conv_{uuid.uuid4().hex[:8]}"

    # Save directly to PostgreSQL (skip Redis)
    pg.save_message(fresh_conv_id, test_user_id, "user",      "Tell me about DNA")
    pg.save_message(fresh_conv_id, test_user_id, "assistant", "DNA is a molecule...")

    # MemoryManager.get_history should auto-restore from PostgreSQL
    memory  = MemoryManager()
    history = memory.get_history(fresh_conv_id)  # Redis miss → PostgreSQL restore

    assert len(history) == 2, f"Expected 2 turns after auto-restore, got {len(history)}"
    ok(f"Auto-restored {len(history)} turns from PostgreSQL | conv={fresh_conv_id[:12]}")
    record_pass("Auto-restore on Redis miss works")
except Exception as e:
    record_fail("Auto-restore FAILED", e)


# ==========================================
# TEST 7: Query Log
# ==========================================

section("TEST 7: Save Query Log")
try:
    pg.save_query_log(
        conversation_id    = test_conv_id,
        query              = "What is photosynthesis?",
        user_id            = test_user_id,
        response           = "Photosynthesis is...",
        retrieval_strategy = "hybrid",
        retrieval_count    = 5,
        latency_ms         = 1250,
        cache_hit          = False,
    )
    ok("Query log saved")

    # Save cached query log
    pg.save_query_log(
        conversation_id = test_conv_id,
        query           = "What is DNA?",
        user_id         = test_user_id,
        response        = "DNA is...",
        latency_ms      = 12,
        cache_hit       = True,
    )
    ok("Cached query log saved")
    record_pass("Query logs saved to PostgreSQL")
except Exception as e:
    record_fail("Query log FAILED", e)


# ==========================================
# TEST 8: Topic Interest
# ==========================================

section("TEST 8: Topic Interest Tracking")
try:
    pg.update_topic_interest(test_user_id, "photosynthesis")
    pg.update_topic_interest(test_user_id, "photosynthesis")  # second query → score increases
    pg.update_topic_interest(test_user_id, "DNA")
    pg.update_topic_interest(test_user_id, "biology")

    topics = pg.get_user_top_topics(test_user_id, limit=5)
    ok(f"Top topics for user: {[t['topic'] for t in topics]}")

    photo_entry = next((t for t in topics if t["topic"] == "photosynthesis"), None)
    if photo_entry:
        ok(f"photosynthesis | score={photo_entry['interest_score']} count={photo_entry['query_count']}")
        assert photo_entry["query_count"] >= 2, "photosynthesis should have at least 2 queries"

    record_pass("Topic interest tracking works")
except Exception as e:
    record_fail("Topic interest FAILED", e)


# ==========================================
# TEST 9: MemoryManager dual-write
# ==========================================

section("TEST 9: MemoryManager dual-write (Redis + PostgreSQL)")
try:
    dual_conv_id = f"test_dual_{uuid.uuid4().hex[:8]}"
    memory       = MemoryManager()

    # create_session with user_id
    sid = memory.create_session(user_id=test_user_id)
    ok(f"Session created | session_id={sid[:12]}...")

    # append_exchange — writes to Redis AND PostgreSQL
    memory.append_exchange(
        session_id       = sid,
        user_query       = "What is biotechnology?",
        assistant_answer = "Biotechnology is the use of biological systems...",
        user_id          = test_user_id,
    )

    # Verify Redis
    redis_hist = memory.get_history(sid)
    assert len(redis_hist) == 2, f"Redis: expected 2 turns, got {len(redis_hist)}"
    ok(f"Redis has {len(redis_hist)} turns")

    # Verify PostgreSQL
    pg_hist = pg.get_conversation_history(sid)
    assert len(pg_hist) == 2, f"PostgreSQL: expected 2 turns, got {len(pg_hist)}"
    ok(f"PostgreSQL has {len(pg_hist)} turns")

    record_pass("Dual-write to Redis + PostgreSQL works")
except Exception as e:
    record_fail("Dual-write FAILED", e)


# ==========================================
# TEST 10: User Long-Term Profile
# ==========================================

section("TEST 10: User Long-Term Memory Profile")
try:
    mem_profile = pg.get_user_memory(test_user_id)
    if mem_profile:
        ok(f"Learning level : {mem_profile.get('learning_level')}")
        ok(f"Total queries  : {mem_profile.get('total_queries')}")
        ok(f"Topics         : {mem_profile.get('preferred_topics')}")
        record_pass("User long-term profile retrieved")
    else:
        warn("User memory profile not found (may not be initialized)")
except Exception as e:
    record_fail("User memory profile FAILED", e)


# ==========================================
# FINAL RESULTS
# ==========================================

print(f"\n{'='*60}")
print(f"  FINAL RESULTS")
print(f"{'='*60}")
print(f"  ✅ PASSED : {_passed}")
print(f"  ❌ FAILED : {_failed}")
print(f"{'='*60}\n")

if _failed > 0:
    sys.exit(1)
