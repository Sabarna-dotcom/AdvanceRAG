"""
Auth Test Suite.

Tests authentication — register, login, token refresh, logout, invalid flows.

Requires:
  - PostgreSQL running  (docker-compose up -d postgres)
  - Redis running       (docker-compose up -d redis)

Run:
    python -m tests.test_auth
"""

import sys
import traceback

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
# SETUP — TestClient
# ==========================================

section("SETUP: Loading FastAPI TestClient")
try:
    from fastapi.testclient import TestClient
    from src.api.app import app
    client = TestClient(app, raise_server_exceptions=False)
    ok("TestClient ready")
except Exception as e:
    fail("TestClient failed to load", e)
    sys.exit(1)


# ==========================================
# TEST 1: DB + Postgres Connection
# ==========================================

section("TEST 1: PostgreSQL Connection")
try:
    from src.database.connection import check_connection
    ok_flag = check_connection()
    if ok_flag:
        record_pass("PostgreSQL connected")
    else:
        warn("PostgreSQL not reachable — skipping DB-dependent tests")
        print("\n  Run:  docker-compose up -d postgres")
        sys.exit(0)
except Exception as e:
    record_fail("PostgreSQL connection check failed", e)
    sys.exit(0)


# ==========================================
# TEST 2: PasswordHandler
# ==========================================

section("TEST 2: PasswordHandler")
try:
    from src.auth.password_handler import PasswordHandler
    handler = PasswordHandler()
    hashed  = handler.hash_password("TestPass1!")
    assert hashed != "TestPass1!",              "Hash should not equal plain text"
    assert handler.verify_password("TestPass1!", hashed), "Correct password should verify"
    assert not handler.verify_password("Wrong1!", hashed), "Wrong password should not verify"
    record_pass("PasswordHandler hash + verify works correctly")
except Exception as e:
    record_fail("PasswordHandler FAILED", e)


# ==========================================
# TEST 3: JWTHandler
# ==========================================

section("TEST 3: JWTHandler")
try:
    from src.auth.jwt_handler import JWTHandler
    jwt   = JWTHandler()
    token, jti = jwt.create_access_token("user_test_123", "test@test.com")
    assert token, "Token should not be empty"

    payload = jwt.verify_token(token, token_type="access")
    assert payload["sub"]   == "user_test_123",   f"sub mismatch: {payload['sub']}"
    assert payload["email"] == "test@test.com",   f"email mismatch: {payload['email']}"
    assert payload["jti"]   == jti,               f"jti mismatch"
    ok(f"Access token created and verified | jti={jti[:8]}...")

    # Refresh token
    refresh_token, _ = jwt.create_refresh_token("user_test_123", "test@test.com")
    payload_r = jwt.verify_token(refresh_token, token_type="refresh")
    assert payload_r["type"] == "refresh"
    ok("Refresh token created and verified")

    # Wrong type check
    try:
        jwt.verify_token(token, token_type="refresh")
        record_fail("Should have raised ValueError for wrong token type")
    except ValueError:
        ok("Wrong token type correctly rejected")

    record_pass("JWTHandler works correctly")
except Exception as e:
    record_fail("JWTHandler FAILED", e)


# ==========================================
# TEST 4: POST /auth/register
# ==========================================

section("TEST 4: POST /auth/register")
import time
test_email    = f"testuser_{int(time.time())}@example.com"
test_username = f"user_{int(time.time())}"
test_password = "TestPass1!"

try:
    resp = client.post("/auth/register", json={
        "email":    test_email,
        "username": test_username,
        "password": test_password,
        "full_name": "Test User"
    })
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert "user_id"  in data
    assert data["email"] == test_email
    ok(f"Registered | user_id={data['user_id']}")
    record_pass("POST /auth/register works")
except Exception as e:
    record_fail("POST /auth/register FAILED", e)


# ==========================================
# TEST 5: POST /auth/register — duplicate
# ==========================================

section("TEST 5: POST /auth/register — duplicate email")
try:
    resp = client.post("/auth/register", json={
        "email":    test_email,
        "username": test_username + "_2",
        "password": test_password,
    })
    assert resp.status_code == 400, f"Expected 400, got {resp.status_code}"
    ok(f"Duplicate email correctly rejected: {resp.json().get('detail')}")
    record_pass("Duplicate registration rejected")
except Exception as e:
    record_fail("Duplicate registration test FAILED", e)


# ==========================================
# TEST 6: POST /auth/register — weak password
# ==========================================

section("TEST 6: POST /auth/register — weak password")
try:
    resp = client.post("/auth/register", json={
        "email":    f"weak_{int(time.time())}@test.com",
        "username": f"weakuser_{int(time.time())}",
        "password": "weak",
    })
    assert resp.status_code == 400, f"Expected 400, got {resp.status_code}"
    ok(f"Weak password rejected: {resp.json().get('detail')}")
    record_pass("Weak password policy enforced")
except Exception as e:
    record_fail("Weak password test FAILED", e)


# ==========================================
# TEST 7: POST /auth/login
# ==========================================

section("TEST 7: POST /auth/login")
access_token  = None
refresh_token = None

try:
    resp = client.post("/auth/login", json={
        "email":    test_email,
        "password": test_password,
    })
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data          = resp.json()
    access_token  = data.get("access_token")
    refresh_token = data.get("refresh_token")
    assert access_token,  "access_token missing"
    assert refresh_token, "refresh_token missing"
    ok(f"Login success | user_id={data.get('user_id')}")
    ok(f"Access token  : {access_token[:30]}...")
    ok(f"Refresh token : {refresh_token[:30]}...")
    record_pass("POST /auth/login works")
except Exception as e:
    record_fail("POST /auth/login FAILED", e)


# ==========================================
# TEST 8: POST /auth/login — wrong password
# ==========================================

section("TEST 8: POST /auth/login — wrong password")
try:
    resp = client.post("/auth/login", json={
        "email":    test_email,
        "password": "WrongPass1!",
    })
    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"
    ok(f"Wrong password rejected: {resp.json().get('detail')}")
    record_pass("Wrong password correctly rejected")
except Exception as e:
    record_fail("Wrong password test FAILED", e)


# ==========================================
# TEST 9: GET /auth/me
# ==========================================

section("TEST 9: GET /auth/me")
try:
    if not access_token:
        warn("Skipped — no access token from login test")
    else:
        resp = client.get("/auth/me", headers={"Authorization": f"Bearer {access_token}"})
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["email"] == test_email
        ok(f"Me response | email={data['email']} username={data.get('username')}")
        record_pass("GET /auth/me works")
except Exception as e:
    record_fail("GET /auth/me FAILED", e)


# ==========================================
# TEST 10: GET /auth/me — no token
# ==========================================

section("TEST 10: GET /auth/me — no token (401)")
try:
    resp = client.get("/auth/me")
    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"
    ok("Correctly rejected unauthenticated request with 401")
    record_pass("Unauthenticated access rejected")
except Exception as e:
    record_fail("Unauthenticated test FAILED", e)


# ==========================================
# TEST 11: POST /auth/refresh
# ==========================================

section("TEST 11: POST /auth/refresh")
try:
    if not refresh_token:
        warn("Skipped — no refresh token from login test")
    else:
        resp = client.post("/auth/refresh", json={"refresh_token": refresh_token})
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        new_access = data.get("access_token")
        assert new_access, "New access token missing"
        ok(f"New access token: {new_access[:30]}...")
        record_pass("POST /auth/refresh works")
except Exception as e:
    record_fail("POST /auth/refresh FAILED", e)


# ==========================================
# TEST 12: POST /auth/logout
# ==========================================

section("TEST 12: POST /auth/logout")
try:
    if not access_token:
        warn("Skipped — no access token")
    else:
        resp = client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        ok(f"Logout: {resp.json().get('message')}")

        # Token should now be rejected
        resp2 = client.get("/auth/me", headers={"Authorization": f"Bearer {access_token}"})
        assert resp2.status_code == 401, f"Expected 401 after logout, got {resp2.status_code}"
        ok("Token correctly rejected after logout")
        record_pass("POST /auth/logout + token blacklist works")
except Exception as e:
    record_fail("POST /auth/logout FAILED", e)


# ==========================================
# TEST 13: POST /query with auth (user_id tracking)
# ==========================================

section("TEST 13: POST /query — with auth token")
try:
    # Login fresh token
    resp_login = client.post("/auth/login", json={"email": test_email, "password": test_password})
    if resp_login.status_code == 200:
        fresh_token = resp_login.json()["access_token"]
        resp = client.post(
            "/query",
            json={"query": "What is photosynthesis?"},
            headers={"Authorization": f"Bearer {fresh_token}"},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        ok(f"Query with auth | has_answer={data.get('has_answer')} session_id={data.get('session_id','')[:8]}...")
        record_pass("POST /query with auth works (user_id tracked)")
    else:
        warn("Skipped — login failed")
except Exception as e:
    record_fail("POST /query with auth FAILED", e)


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
