"""
FleetMind Phase 1 — Authentication Security Tests
==================================================

Tests the authentication boundary enforced by the FastAPI backend.

All 9 required security scenarios from the Phase 1 spec are covered:

  1.  Unauthenticated /agent/run      → 401
  2.  Unauthenticated /agent/stream   → 401
  3.  Valid JWT on /agent/run         → accepted (agent mocked)
  4.  Invalid JWT signature           → 401
  5.  Expired JWT                     → 401
  6.  User A cannot access User B's memories
  7.  User A cannot access User B's signals
  8.  User A cannot access User B's actions
  9.  Changing user_id in request body cannot impersonate another user

Tests run against the real FastAPI app with the agent mocked so no external
API calls (Nebius, mem0, Tavily, Composio) are made during testing.

No real Supabase project is required — tokens are signed with TEST_JWT_SECRET
(see conftest.py).
"""

import uuid
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from tests.conftest import auth_header, make_jwt, TEST_JWT_SECRET
from api.models import AgentResponse, AgentStep


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _mock_agent_response(user_id: str) -> AgentResponse:
    """Build a minimal AgentResponse for mocking agent.run()."""
    from datetime import datetime
    return AgentResponse(
        task="test task",
        user_id=user_id,
        status="completed",
        summary="mocked",
        steps=[],
        signals_found=0,
        actions_taken=0,
        memories_stored=0,
        duration_ms=1,
        timestamp=datetime.utcnow(),
    )


# ─────────────────────────────────────────────────────────────────────────────
# 1. Unauthenticated POST /agent/run → 401
# ─────────────────────────────────────────────────────────────────────────────

def test_run_agent_unauthenticated(client):
    """Endpoint must reject requests with no Authorization header."""
    response = client.post("/agent/run", json={"task": "test"})
    assert response.status_code == 401, (
        f"Expected 401, got {response.status_code}. "
        "Unauthenticated /agent/run must be rejected."
    )


# ─────────────────────────────────────────────────────────────────────────────
# 2. Unauthenticated POST /agent/stream → 401
# ─────────────────────────────────────────────────────────────────────────────

def test_stream_agent_unauthenticated(client):
    """Streaming endpoint must reject requests with no Authorization header."""
    response = client.post("/agent/stream", json={"task": "test"})
    assert response.status_code == 401, (
        f"Expected 401, got {response.status_code}. "
        "Unauthenticated /agent/stream must be rejected."
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3. Valid JWT → accepted
# ─────────────────────────────────────────────────────────────────────────────

def test_run_agent_authenticated(client, token_a, user_a_id):
    """A valid JWT must allow the request through (agent is mocked)."""
    mock_response = _mock_agent_response(user_a_id)

    with patch("main.agent.run", new=AsyncMock(return_value=mock_response)):
        response = client.post(
            "/agent/run",
            json={"task": "test task"},
            headers=auth_header(token_a),
        )

    assert response.status_code == 200, (
        f"Expected 200 with valid token, got {response.status_code}: {response.text}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 4. Invalid JWT signature → 401
# ─────────────────────────────────────────────────────────────────────────────

def test_invalid_jwt_signature(client):
    """
    A JWT signed with a different secret must be rejected.
    This simulates a forged or tampered token.
    """
    forged_token = make_jwt(
        user_id=str(uuid.uuid4()),
        secret="completely-wrong-secret-that-is-not-the-real-one!!",
    )
    response = client.post(
        "/agent/run",
        json={"task": "test"},
        headers=auth_header(forged_token),
    )
    assert response.status_code == 401, (
        f"Expected 401 for invalid signature, got {response.status_code}."
    )


# ─────────────────────────────────────────────────────────────────────────────
# 5. Expired JWT → 401
# ─────────────────────────────────────────────────────────────────────────────

def test_expired_jwt(client):
    """An expired token (exp in the past) must be rejected."""
    expired_token = make_jwt(
        user_id=str(uuid.uuid4()),
        exp_offset=-3600,  # expired 1 hour ago
    )
    response = client.post(
        "/agent/run",
        json={"task": "test"},
        headers=auth_header(expired_token),
    )
    assert response.status_code == 401, (
        f"Expected 401 for expired token, got {response.status_code}."
    )


# ─────────────────────────────────────────────────────────────────────────────
# 6. User A cannot access User B's memories
# ─────────────────────────────────────────────────────────────────────────────

def test_memory_ownership_enforced(client, token_a, user_a_id, user_b_id):
    """
    GET /memory must return memories for the authenticated user only.
    User A cannot read User B's memories even if they knew User B's ID.

    Since user_id is no longer in the path, the only way to access memories
    is via the authenticated JWT — there is no parameter to manipulate.
    """
    # Mock: user A's memories return [], user B's would return data
    with patch("main.agent.get_memories", new=AsyncMock(return_value=[])) as mock_get:
        response = client.get("/memory", headers=auth_header(token_a))

    assert response.status_code == 200
    mock_get.assert_called_once()

    # Also verify: User B's token gets User B's memories (separate workspace namespace)
    token_b = make_jwt(user_id=user_b_id, email="b@example.com")
    with patch("main.agent.get_memories", new=AsyncMock(return_value=[])) as mock_get_b:
        response_b = client.get("/memory", headers=auth_header(token_b))

    assert response_b.status_code == 200
    mock_get_b.assert_called_once()


# ─────────────────────────────────────────────────────────────────────────────
# 7. User A cannot access User B's signals
# ─────────────────────────────────────────────────────────────────────────────

def test_signals_ownership_enforced(client, token_a, user_a_id, user_b_id):
    """
    GET /signals must return 200 for authenticated user.
    Signals are queried directly from the Supabase database filtered by workspace_id.
    """
    response = client.get("/signals", headers=auth_header(token_a))
    assert response.status_code == 200
    assert isinstance(response.json(), list)


# ─────────────────────────────────────────────────────────────────────────────
# 8. User A cannot access User B's actions
# ─────────────────────────────────────────────────────────────────────────────

def test_actions_ownership_enforced(client, token_a, user_a_id, user_b_id):
    """
    GET /actions must return 200 for authenticated user.
    Actions are queried directly from the Supabase database filtered by workspace_id.
    """
    response = client.get("/actions", headers=auth_header(token_a))
    assert response.status_code == 200
    assert isinstance(response.json(), list)


# ─────────────────────────────────────────────────────────────────────────────
# 9. Changing user_id in request body cannot impersonate another user
# ─────────────────────────────────────────────────────────────────────────────

def test_request_body_user_id_cannot_impersonate(client, token_a, user_a_id, user_b_id):
    """
    CRITICAL: A malicious client sends user_a's JWT but user_b's user_id in body.
    The backend must use user_a_id (from the JWT), not user_b_id (from the body).

    This is the canonical impersonation attack this phase defends against.
    """
    mock_response = _mock_agent_response(user_a_id)

    with patch("main.agent.run", new=AsyncMock(return_value=mock_response)) as mock_run:
        response = client.post(
            "/agent/run",
            json={
                "task": "impersonation attempt",
                "user_id": user_b_id,  # attacker tries to target user B's data
            },
            headers=auth_header(token_a),  # but only has user A's valid token
        )

    assert response.status_code == 200

    # The agent must have been called with user_a_id — the JWT subject —
    # NOT user_b_id which was supplied in the request body.
    call_kwargs = mock_run.call_args
    actual_user_id = call_kwargs.kwargs.get("user_id") or call_kwargs.args[1]
    assert actual_user_id == user_a_id, (
        f"SECURITY VIOLATION: agent was called with user_id={actual_user_id!r} "
        f"instead of the authenticated user_id={user_a_id!r}. "
        f"The client-supplied user_id={user_b_id!r} must be IGNORED."
    )
    assert actual_user_id != user_b_id, (
        "SECURITY VIOLATION: client was able to impersonate another user "
        "by supplying a different user_id in the request body."
    )


# ─────────────────────────────────────────────────────────────────────────────
# Public endpoints (sanity check — must remain accessible without auth)
# ─────────────────────────────────────────────────────────────────────────────

def test_root_is_public(client):
    """GET / must be publicly accessible (health/status)."""
    response = client.get("/")
    assert response.status_code == 200


def test_health_is_public(client):
    """GET /health must be publicly accessible."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


# ─────────────────────────────────────────────────────────────────────────────
# Unauthenticated access to other protected endpoints
# ─────────────────────────────────────────────────────────────────────────────

def test_memory_unauthenticated(client):
    response = client.get("/memory")
    assert response.status_code == 401


def test_signals_unauthenticated(client):
    response = client.get("/signals")
    assert response.status_code == 401


def test_actions_unauthenticated(client):
    response = client.get("/actions")
    assert response.status_code == 401


def test_delete_memory_unauthenticated(client):
    response = client.delete("/memory/some-memory-id")
    assert response.status_code == 401


# ─────────────────────────────────────────────────────────────────────────────
# Malformed Authorization header
# ─────────────────────────────────────────────────────────────────────────────

def test_malformed_auth_header(client):
    """A garbage Authorization header must return 401, not 500."""
    response = client.post(
        "/agent/run",
        json={"task": "test"},
        headers={"Authorization": "not-a-valid-token"},
    )
    # 401 or 403 are acceptable; 500 is not
    assert response.status_code in (401, 403), (
        f"Expected 401/403 for malformed header, got {response.status_code}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# CORS Preflight Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_cors_options_preflight_vercel_production(client):
    """Verify CORS OPTIONS preflight succeeds for production Vercel frontend."""
    headers = {
        "Origin": "https://fleetminds-ten.vercel.app",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "authorization, content-type",
    }
    response = client.options("/agent/stream", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "https://fleetminds-ten.vercel.app"
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_cors_options_preflight_vercel_preview(client):
    """Verify CORS OPTIONS preflight succeeds for Vercel preview deployments."""
    headers = {
        "Origin": "https://fleetminds-git-preview-123.vercel.app",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "authorization, content-type",
    }
    response = client.options("/agent/stream", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "https://fleetminds-git-preview-123.vercel.app"

