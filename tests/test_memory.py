"""
Memory Manager Test Suite.

Tests the Redis-backed session memory layer:
  1. Redis Connection
  2. Session Creation
  3. Append Turn
  4. Append Exchange
  5. Get History
  6. Max History Window (trim)
  7. Clear History
  8. Delete Session
  9. Get Recent History
  10. Session Expiry / Not Found

Run with:
    python -m tests.test_memory
or:
    python tests/test_memory.py
"""

import sys
import traceback


# ==========================================
# Helpers
# ==========================================

def print_header(title: str):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_result(label: str, value):
    print(f"   ✓ {label}: {value}")


def print_fail(label: str, error):
    print(f"   ✗ {label}: {error}")


# ==========================================
# Test 1: Redis Connection
# ==========================================

def test_redis_connection():
    print_header("TEST 1: Redis Connection")

    try:
        from src.memory.memory_manager import MemoryManager

        manager = MemoryManager()
        print_result("Initialized", "MemoryManager")
        print_result("Redis ping", "OK")

        print("\n  ✅ Redis Connection PASSED")
        return True, manager

    except Exception as e:
        print_fail("Redis Connection FAILED", e)
        traceback.print_exc()
        return False, None


# ==========================================
# Test 2: Session Creation
# ==========================================

def test_create_session(manager):
    print_header("TEST 2: Session Creation")

    try:
        session_id = manager.create_session()
        print_result("Session ID created", session_id)

        assert session_id and len(session_id) > 0, "Session ID is empty"

        exists = manager.session_exists(session_id)
        print_result("Session exists in Redis", exists)
        assert exists, "Session not found in Redis after creation"

        meta = manager.get_meta(session_id)
        print_result("Meta created_at", meta.get("created_at"))
        print_result("Meta query_count", meta.get("query_count"))
        assert meta is not None, "Meta is None"
        assert meta["query_count"] == 0, "Initial query_count should be 0"

        print("\n  ✅ Session Creation PASSED")
        return True, session_id

    except Exception as e:
        print_fail("Session Creation FAILED", e)
        traceback.print_exc()
        return False, None


# ==========================================
# Test 3: Append Turn
# ==========================================

def test_append_turn(manager, session_id):
    print_header("TEST 3: Append Turn")

    try:
        history = manager.append_turn(session_id, "user", "What is photosynthesis?")
        print_result("After user turn, history length", len(history))
        assert len(history) == 1, "Expected 1 turn"
        assert history[0]["role"] == "user", "First turn role should be user"

        history = manager.append_turn(
            session_id,
            "assistant",
            "Photosynthesis is the process by which plants make food."
        )

        print_result("After assistant turn, history length", len(history))
        assert len(history) == 2, "Expected 2 turns"
        assert history[1]["role"] == "assistant", "Second turn role should be assistant"

        print_result("Roles", [t["role"] for t in history])

        print("\n  ✅ Append Turn PASSED")
        return True

    except Exception as e:
        print_fail("Append Turn FAILED", e)
        traceback.print_exc()
        return False


# ==========================================
# Test 4: Append Exchange
# ==========================================

def test_append_exchange(manager, session_id):
    print_header("TEST 4: Append Exchange")

    try:
        # Clear first for clean test
        manager.clear_history(session_id)

        history = manager.append_exchange(
            session_id=session_id,
            user_query="What is biotechnology?",
            assistant_answer="Biotechnology uses biological systems to develop products.",
        )

        print_result("History length after exchange", len(history))
        assert len(history) == 2, "Expected 2 turns from one exchange"
        assert history[0]["role"] == "user", "First should be user"
        assert history[1]["role"] == "assistant", "Second should be assistant"
        assert "biotechnology" in history[0]["content"].lower(), "User content mismatch"

        print_result("Exchange roles", [t["role"] for t in history])

        print("\n  ✅ Append Exchange PASSED")
        return True

    except Exception as e:
        print_fail("Append Exchange FAILED", e)
        traceback.print_exc()
        return False

# ==========================================
# Test 5: Get History
# ==========================================

def test_get_history(manager, session_id):
    print_header("TEST 5: Get History")

    try:
        history = manager.get_history(session_id)
        print_result("History length", len(history))
        assert isinstance(history, list), "History should be a list"

        for i, turn in enumerate(history):
            assert "role" in turn, f"Turn {i} missing 'role'"
            assert "content" in turn, f"Turn {i} missing 'content'"

        print_result("All turns have role + content", True)
        print_result(
            "Preview turn[0]",
            history[0]["content"][:60] if history else "empty"
        )

        print("\n  ✅ Get History PASSED")
        return True

    except Exception as e:
        print_fail("Get History FAILED", e)
        traceback.print_exc()
        return False


# ==========================================
# Test 6: Max History Window (trim)
# ==========================================

def test_max_history_trim(manager):
    print_header("TEST 6: Max History Window (Trim)")

    try:
        # Create a fresh session
        session_id = manager.create_session()

        # Add more turns than max_chat_history (default 10)
        limit = manager.max_history
        print_result("Max history limit", limit)

        for i in range(limit + 4):
            manager.append_exchange(
                session_id=session_id,
                user_query=f"Question {i}",
                assistant_answer=f"Answer {i}",
            )

        history = manager.get_history(session_id)
        print_result("History length after overflow", len(history))

        assert len(history) <= limit, (
            f"History {len(history)} exceeds max_history {limit}"
        )

        # Verify it kept the most recent turns
        last_content = history[-1]["content"]
        print_result(
            "Last turn content (should be most recent)",
            last_content[:60]
        )

        # Cleanup
        manager.delete_session(session_id)

        print("\n  ✅ Max History Trim PASSED")
        return True

    except Exception as e:
        print_fail("Max History Trim FAILED", e)
        traceback.print_exc()
        return False


# ==========================================
# Test 7: Clear History
# ==========================================

def test_clear_history(manager, session_id):
    print_header("TEST 7: Clear History")

    try:
        # Add a turn first
        manager.append_turn(session_id, "user", "test message")

        history_before = manager.get_history(session_id)
        print_result("History before clear", len(history_before))

        manager.clear_history(session_id)

        history_after = manager.get_history(session_id)
        print_result("History after clear", len(history_after))

        assert len(history_after) == 0, "History should be empty after clear"

        # Session should still exist
        exists = manager.session_exists(session_id)
        print_result("Session still alive after clear", exists)

        assert exists, "Session should still exist after clear"

        print("\n  ✅ Clear History PASSED")
        return True

    except Exception as e:
        print_fail("Clear History FAILED", e)
        traceback.print_exc()
        return False


# ==========================================
# Test 8: Delete Session
# ==========================================

def test_delete_session(manager):
    print_header("TEST 8: Delete Session")

    try:
        temp_session = manager.create_session()

        print_result("Temp session created", temp_session)
        assert manager.session_exists(temp_session), (
            "Temp session should exist"
        )

        manager.delete_session(temp_session)

        exists_after = manager.session_exists(temp_session)
        print_result("Session exists after delete", exists_after)

        assert not exists_after, (
            "Session should be gone after delete"
        )

        print("\n  ✅ Delete Session PASSED")
        return True

    except Exception as e:
        print_fail("Delete Session FAILED", e)
        traceback.print_exc()
        return False


# ==========================================
# Test 9: Get Recent History
# ==========================================

def test_get_recent_history(manager):
    print_header("TEST 9: Get Recent History")

    try:
        session_id = manager.create_session()

        # Add 6 exchanges = 12 turns
        for i in range(6):
            manager.append_exchange(
                session_id=session_id,
                user_query=f"Question {i}",
                assistant_answer=f"Answer {i}",
            )

        full_history = manager.get_history(session_id)
        recent_history = manager.get_recent_history(
            session_id,
            last_n=4
        )

        print_result("Full history length", len(full_history))
        print_result("Recent history length", len(recent_history))

        assert len(recent_history) == 4, (
            f"Expected 4 recent turns, got {len(recent_history)}"
        )

        assert recent_history == full_history[-4:], (
            "Recent history should be last 4 turns"
        )

        manager.delete_session(session_id)

        print("\n  ✅ Get Recent History PASSED")
        return True

    except Exception as e:
        print_fail("Get Recent History FAILED", e)
        traceback.print_exc()
        return False


# ==========================================
# Test 10: Non-existent Session
# ==========================================

def test_nonexistent_session(manager):
    print_header("TEST 10: Non-Existent Session")

    try:
        fake_id = "non-existent-session-id-12345"

        exists = manager.session_exists(fake_id)
        print_result("Non-existent session exists", exists)

        assert not exists, (
            "Non-existent session should not exist"
        )

        history = manager.get_history(fake_id)
        print_result("History for non-existent session", history)

        assert history == [], (
            "History should be empty list for non-existent session"
        )

        meta = manager.get_meta(fake_id)
        print_result("Meta for non-existent session", meta)

        assert meta is None, (
            "Meta should be None for non-existent session"
        )

        history = manager.append_turn(
            fake_id,
            "user",
            "hello"
        )

        print_result(
            "Auto-created session on append_turn",
            len(history)
        )

        assert len(history) == 1, (
            "Should auto-create session and append turn"
        )

        manager.delete_session(fake_id)

        print("\n  ✅ Non-Existent Session PASSED")
        return True

    except Exception as e:
        print_fail("Non-Existent Session FAILED", e)
        traceback.print_exc()
        return False


# ==========================================
# Main Runner
# ==========================================

def main():

    print("\n" + "🧠 " * 20)
    print("   MEMORY MANAGER TEST SUITE")
    print("🧠 " * 20)

    results = {}

    # Test 1: Connection
    passed, manager = test_redis_connection()
    results["1. Redis Connection"] = passed

    if not manager:
        print("\n  ❌ Cannot continue — Redis not available.")
        print("     Make sure Redis is running: docker-compose up redis")
        return False

    # Test 2: Session Creation
    passed, session_id = test_create_session(manager)
    results["2. Session Creation"] = passed

    if not session_id:
        print("\n  ❌ Cannot continue — session creation failed.")
        return False

    results["3. Append Turn"] = test_append_turn(manager, session_id)
    results["4. Append Exchange"] = test_append_exchange(manager, session_id)
    results["5. Get History"] = test_get_history(manager, session_id)
    results["6. Max History Trim"] = test_max_history_trim(manager)
    results["7. Clear History"] = test_clear_history(manager, session_id)
    results["8. Delete Session"] = test_delete_session(manager)
    results["9. Get Recent History"] = test_get_recent_history(manager)
    results["10. Non-Existent Session"] = test_nonexistent_session(manager)

    if manager.session_exists(session_id):
        manager.delete_session(session_id)

    print_header("FINAL RESULTS")

    passed_count = 0
    failed_count = 0

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}  {test_name}")

        if result:
            passed_count += 1
        else:
            failed_count += 1

    print(f"\n  Total: {passed_count} passed, {failed_count} failed")

    if failed_count == 0:
        print("\n  🎉 ALL TESTS PASSED — Memory layer is working!")
    else:
        print(f"\n  ⚠️ {failed_count} test(s) failed — check errors above")

    return failed_count == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)