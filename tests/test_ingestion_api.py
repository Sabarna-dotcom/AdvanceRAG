"""
Ingestion API Test Suite.

Tests ingestion API endpoints using FastAPI TestClient.
Requires: Qdrant running  →  docker-compose up -d qdrant

⚠️ WARNING: DELETE /ingest/wipe and POST /ingest/reindex are DESTRUCTIVE.
           They will wipe your Qdrant data. They are SKIPPED by default.
           Set RUN_DESTRUCTIVE=True below to enable them.

Run:
    python -m tests.test_ingestion_api
"""

import sys
import traceback

# ==========================================
# Set to True ONLY if you are OK wiping data
# ==========================================
RUN_DESTRUCTIVE = False

# ==========================================
# Helpers
# ==========================================

def section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def ok(msg):    print(f"  ✓  {msg}")
def warn(msg):  print(f"  ⚠️  {msg}")
def skip(msg):  print(f"  ⏭️  SKIPPED: {msg}")
def fail(msg, exc=None):
    print(f"  ✗  {msg}")
    if exc:
        traceback.print_exc()

_passed = 0
_failed = 0
_skipped = 0

def record_pass(label):
    global _passed
    _passed += 1
    ok(label)

def record_fail(label, exc=None):
    global _failed
    _failed += 1
    fail(label, exc)

def record_skip(label):
    global _skipped
    _skipped += 1
    skip(label)


# ==========================================
# Boot TestClient
# ==========================================

section("SETUP: Loading FastAPI TestClient")
try:
    from fastapi.testclient import TestClient
    from src.api.app import app
    client = TestClient(app, raise_server_exceptions=False)
    ok("TestClient ready")
except Exception as e:
    fail("Failed to load TestClient", e)
    sys.exit(1)


# ==========================================
# TEST 1: GET /ingest/status
# ==========================================

section("TEST 1: GET /ingest/status")
try:
    resp = client.get("/ingest/status")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    ok(f"Status code: {resp.status_code}")
    ok(f"Qdrant reachable: {data.get('qdrant_reachable')}")
    collections = data.get("collections", [])
    for col in collections:
        ok(f"  Collection: {col['name']} — {col['points']} points")
    tracker = data.get("tracker_state", {})
    if tracker:
        ok(f"  PDF tracked files   : {tracker.get('pdf_tracked_files', 0)}")
        ok(f"  Audio tracked files : {tracker.get('audio_tracked_files', 0)}")
    record_pass("GET /ingest/status works")
except Exception as e:
    record_fail("GET /ingest/status FAILED", e)


# ==========================================
# TEST 2: DELETE /ingest/file — non-existent file (safe)
# ==========================================

section("TEST 2: DELETE /ingest/file — non-existent file")
try:
    resp = client.request(
        "DELETE",
        "/ingest/file",
        json={"filename": "nonexistent_file.pdf", "collection": "pdf"},
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    ok(f"Status code: {resp.status_code}")
    ok(f"Success flag : {data.get('success')}")
    ok(f"Message      : {data.get('message')}")
    record_pass("DELETE /ingest/file handles non-existent file gracefully")
except Exception as e:
    record_fail("DELETE /ingest/file FAILED", e)


# ==========================================
# TEST 3: DELETE /ingest/file — audio collection (safe)
# ==========================================

section("TEST 3: DELETE /ingest/file — audio non-existent")
try:
    resp = client.request(
        "DELETE",
        "/ingest/file",
        json={"filename": "nonexistent_audio.json", "collection": "audio"},
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    ok(f"Status: {resp.status_code} | success={data.get('success')} | msg={data.get('message')}")
    record_pass("DELETE /ingest/file (audio) handles gracefully")
except Exception as e:
    record_fail("DELETE /ingest/file audio FAILED", e)


# ==========================================
# TEST 4: DELETE /ingest/file — missing fields (validation)
# ==========================================

section("TEST 4: DELETE /ingest/file — bad request body")
try:
    resp = client.request(
        "DELETE",
        "/ingest/file",
        json={"filename": "something.pdf"},   # missing 'collection'
    )
    assert resp.status_code == 422, f"Expected 422 validation error, got {resp.status_code}"
    ok(f"Correctly rejected bad body with 422")
    record_pass("DELETE /ingest/file validates request body")
except Exception as e:
    record_fail("DELETE /ingest/file validation FAILED", e)


# ==========================================
# TEST 5: DELETE /ingest/wipe  ⚠️ DESTRUCTIVE
# ==========================================

section("TEST 5: DELETE /ingest/wipe  ⚠️ DESTRUCTIVE")
if not RUN_DESTRUCTIVE:
    record_skip("RUN_DESTRUCTIVE=False — set to True in this file to run")
else:
    try:
        warn("This will DELETE all Qdrant vectors and reset tracker state!")
        resp = client.delete("/ingest/wipe")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        ok(f"PDF collection wiped   : {data.get('pdf_collection_wiped')}")
        ok(f"Audio collection wiped : {data.get('audio_collection_wiped')}")
        ok(f"Tracker reset          : {data.get('tracker_reset')}")
        ok(f"Message                : {data.get('message')}")
        record_pass("DELETE /ingest/wipe completed")
    except Exception as e:
        record_fail("DELETE /ingest/wipe FAILED", e)


# ==========================================
# TEST 6: POST /ingest/reindex  ⚠️ DESTRUCTIVE + SLOW
# ==========================================

section("TEST 6: POST /ingest/reindex  ⚠️ DESTRUCTIVE + SLOW")
if not RUN_DESTRUCTIVE:
    record_skip("RUN_DESTRUCTIVE=False — set to True in this file to run")
else:
    try:
        warn("This will wipe + re-ingest ALL data. May take several minutes...")
        resp = client.post("/ingest/reindex", timeout=600)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        ok(f"Overall status       : {data.get('overall_status')}")
        ok(f"Total chunks indexed : {data.get('total_chunks_indexed')}")
        for r in data.get("results", []):
            ok(f"  [{r['pipeline']}] status={r['status']} chunks={r['chunks_indexed']}")
        record_pass("POST /ingest/reindex completed")
    except Exception as e:
        record_fail("POST /ingest/reindex FAILED", e)


# ==========================================
# TEST 7: POST /ingest/pdf — incremental (safe, skips if no new files)
# ==========================================

section("TEST 7: POST /ingest/pdf — incremental")
try:
    resp = client.post("/ingest/pdf")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    ok(f"Overall status : {data.get('overall_status')}")
    for r in data.get("results", []):
        ok(f"  [{r['pipeline']}] status={r['status']} | new={r.get('new_files',[])} skipped={r.get('skipped_count',0)}")
    record_pass("POST /ingest/pdf (incremental) works")
except Exception as e:
    record_fail("POST /ingest/pdf FAILED", e)


# ==========================================
# TEST 8: POST /ingest/audio — incremental (safe)
# ==========================================

section("TEST 8: POST /ingest/audio — incremental")
try:
    resp = client.post("/ingest/audio")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    ok(f"Overall status : {data.get('overall_status')}")
    for r in data.get("results", []):
        ok(f"  [{r['pipeline']}] status={r['status']} | new={r.get('new_files',[])} skipped={r.get('skipped_count',0)}")
    record_pass("POST /ingest/audio (incremental) works")
except Exception as e:
    record_fail("POST /ingest/audio FAILED", e)


# ==========================================
# FINAL SUMMARY
# ==========================================

print(f"\n{'='*60}")
print(f"  FINAL RESULTS")
print(f"{'='*60}")
print(f"  ✅ PASSED  : {_passed}")
print(f"  ❌ FAILED  : {_failed}")
print(f"  ⏭️ SKIPPED : {_skipped}")
print(f"{'='*60}")
if not RUN_DESTRUCTIVE:
    print(f"\n  ℹ️  Destructive tests (wipe/reindex) were skipped.")
    print(f"     Set RUN_DESTRUCTIVE = True at the top of this file to run them.\n")

if _failed > 0:
    sys.exit(1)
 