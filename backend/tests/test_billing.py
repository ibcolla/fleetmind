"""
FleetMind Phase 4 — Billing Integration & Usage Limit Tests
-----------------------------------------------------------
Tests:
  1. Free tier usage enforcement: runs 0 to 9 are permitted (200 OK).
  2. Free tier limit blocking: 10th+ run returns HTTP 402 Payment Required.
  3. Active tier bypass: active subscription workspaces bypass the usage limit.
  4. Stripe Webhook sync: subscription created/deleted events update DB.
"""

import pytest
from unittest.mock import AsyncMock, patch
from tests.conftest import auth_header, make_jwt
try:
    from main import _mock_agent_response
except ImportError:
    _mock_agent_response = None


def test_free_tier_workspace_run_permitted(client, token_a, user_a_id, session_mock_db):
    """
    A free tier workspace under the limit (e.g. 0 runs) must be permitted to execute agent tasks.
    """
    # Trigger auto-provisioning
    res = client.get("/signals", headers=auth_header(token_a))
    assert res.status_code == 200

    ws = next(w for w in session_mock_db.store["workspaces"] if w["owner_id"] == user_a_id)
    assert ws["subscription_status"] == "free"
    assert ws["agent_runs_count"] == 0

    # Run agent task
    response = client.post(
        "/agent/run",
        json={"task": "free tier run check"},
        headers=auth_header(token_a),
    )
    assert response.status_code == 200

    # Verify agent_runs_count was incremented
    assert ws["agent_runs_count"] == 1


def test_free_tier_workspace_limit_blocked(client, token_a, user_a_id, session_mock_db):
    """
    A free tier workspace that has reached FREE_TIER_LIMIT (10 runs) must be BLOCKED
    with HTTP 402 Payment Required.
    """
    # Trigger workspace resolution
    client.get("/signals", headers=auth_header(token_a))
    ws = next(w for w in session_mock_db.store["workspaces"] if w["owner_id"] == user_a_id)

    # Set workspace runs to 10 (limit reached)
    ws["subscription_status"] = "free"
    ws["agent_runs_count"] = 10

    # Attempt 11th run
    response = client.post(
        "/agent/run",
        json={"task": "over limit run attempt"},
        headers=auth_header(token_a),
    )
    assert response.status_code == 402
    assert "Free tier limit reached" in response.json()["detail"]

    # Also verify SSE stream is blocked with HTTP 402
    stream_resp = client.post(
        "/agent/stream",
        json={"task": "over limit stream attempt"},
        headers=auth_header(token_a),
    )
    assert stream_resp.status_code == 402


def test_active_subscription_bypasses_limit(client, token_a, user_a_id, session_mock_db):
    """
    Workspaces with subscription_status == 'active' must bypass the 10-run limit completely.
    """
    # Trigger workspace resolution
    client.get("/signals", headers=auth_header(token_a))
    ws = next(w for w in session_mock_db.store["workspaces"] if w["owner_id"] == user_a_id)

    # Set workspace to active subscription with 50 runs
    ws["subscription_status"] = "active"
    ws["agent_runs_count"] = 50

    response = client.post(
        "/agent/run",
        json={"task": "active tier run"},
        headers=auth_header(token_a),
    )
    assert response.status_code == 200
    assert ws["agent_runs_count"] == 51


def test_stripe_webhook_syncs_subscription_created_and_deleted(client, token_a, user_a_id, session_mock_db):
    """
    Stripe Webhook endpoint must process subscription events and update the workspace in DB.
    """
    # Provision workspace and set stripe_customer_id
    client.get("/signals", headers=auth_header(token_a))
    ws = next(w for w in session_mock_db.store["workspaces"] if w["owner_id"] == user_a_id)
    ws["stripe_customer_id"] = "cus_test_9999"
    ws["subscription_status"] = "free"

    # 1. Simulate customer.subscription.created event
    created_payload = {
        "type": "customer.subscription.created",
        "data": {
            "object": {
                "id": "sub_test_1111",
                "customer": "cus_test_9999",
                "status": "active",
            }
        }
    }
    res_created = client.post("/webhooks/stripe", json=created_payload)
    assert res_created.status_code == 200
    assert ws["subscription_status"] == "active"
    assert ws["stripe_subscription_id"] == "sub_test_1111"

    # 2. Simulate customer.subscription.deleted event
    deleted_payload = {
        "type": "customer.subscription.deleted",
        "data": {
            "object": {
                "id": "sub_test_1111",
                "customer": "cus_test_9999",
                "status": "canceled",
            }
        }
    }
    res_deleted = client.post("/webhooks/stripe", json=deleted_payload)
    assert res_deleted.status_code == 200
    assert ws["subscription_status"] == "canceled"
