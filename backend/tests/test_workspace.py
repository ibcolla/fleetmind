"""
FleetMind Phase 2 — Workspace & Database Tests
-----------------------------------------------
Verifies:
  1. Auto-provisioning of a "Personal Workspace" on first login.
  2. Workspace re-use on subsequent calls (idempotent).
  3. GET /signals and GET /actions fetch data from the Supabase database.
  4. Tenant isolation: User A cannot read signals/actions belonging to User B.
"""

import pytest
from tests.conftest import auth_header, make_jwt


def test_workspace_auto_provisioning(client, token_a, user_a_id, session_mock_db):
    """
    On first request, get_current_workspace must auto-provision a 'Personal Workspace'
    and create a workspace_users membership row with role='owner'.
    """
    # Query signals (triggers get_current_workspace dependency)
    response = client.get("/signals", headers=auth_header(token_a))
    assert response.status_code == 200

    # Verify workspace was created in mock DB
    workspaces = session_mock_db.store["workspaces"]
    user_workspaces = [w for w in workspaces if w["owner_id"] == user_a_id]
    assert len(user_workspaces) == 1
    assert user_workspaces[0]["name"] == "Personal Workspace"

    # Verify workspace_users entry was created
    memberships = session_mock_db.store["workspace_users"]
    user_memberships = [m for m in memberships if m["user_id"] == user_a_id]
    assert len(user_memberships) == 1
    assert user_memberships[0]["role"] == "owner"
    assert user_memberships[0]["workspace_id"] == user_workspaces[0]["id"]


def test_workspace_provisioning_idempotent(client, token_a, user_a_id, session_mock_db):
    """
    Subsequent requests must re-use the existing workspace without creating duplicate rows.
    """
    # Call 1
    res1 = client.get("/signals", headers=auth_header(token_a))
    assert res1.status_code == 200

    # Call 2
    res2 = client.get("/actions", headers=auth_header(token_a))
    assert res2.status_code == 200

    # Ensure only 1 workspace exists for user A
    workspaces = [w for w in session_mock_db.store["workspaces"] if w["owner_id"] == user_a_id]
    assert len(workspaces) == 1


def test_tenant_isolation_signals_and_actions(client, token_a, token_b, user_a_id, user_b_id, session_mock_db):
    """
    CRITICAL TENANT ISOLATION:
    User A and User B both make requests, populating signals and actions in their workspaces.
    User A must NOT see User B's signals or actions, and vice versa.
    """
    # Auto-provision workspace for User A
    res_a_sig = client.get("/signals", headers=auth_header(token_a))
    assert res_a_sig.status_code == 200

    # Auto-provision workspace for User B
    res_b_sig = client.get("/signals", headers=auth_header(token_b))
    assert res_b_sig.status_code == 200

    ws_a = next(w for w in session_mock_db.store["workspaces"] if w["owner_id"] == user_a_id)
    ws_b = next(w for w in session_mock_db.store["workspaces"] if w["owner_id"] == user_b_id)

    assert ws_a["id"] != ws_b["id"], "User A and User B must have distinct workspace IDs"

    # Insert signals for User A's workspace and User B's workspace
    session_mock_db.store["signals"].append({
        "id": "sig-a-1",
        "workspace_id": ws_a["id"],
        "content": "User A secret signal",
        "created_at": "2026-09-06T00:00:00Z"
    })
    session_mock_db.store["signals"].append({
        "id": "sig-b-1",
        "workspace_id": ws_b["id"],
        "content": "User B secret signal",
        "created_at": "2026-09-06T00:00:00Z"
    })

    # Insert actions for User A's workspace and User B's workspace
    session_mock_db.store["actions"].append({
        "id": "act-a-1",
        "workspace_id": ws_a["id"],
        "content": "User A secret action",
        "status": "completed",
        "created_at": "2026-09-06T00:00:00Z"
    })
    session_mock_db.store["actions"].append({
        "id": "act-b-1",
        "workspace_id": ws_b["id"],
        "content": "User B secret action",
        "status": "pending",
        "created_at": "2026-09-06T00:00:00Z"
    })

    # User A fetches signals and actions
    resp_a_signals = client.get("/signals", headers=auth_header(token_a)).json()
    resp_a_actions = client.get("/actions", headers=auth_header(token_a)).json()

    # User B fetches signals and actions
    resp_b_signals = client.get("/signals", headers=auth_header(token_b)).json()
    resp_b_actions = client.get("/actions", headers=auth_header(token_b)).json()

    # Assert User A only sees User A's data
    assert len(resp_a_signals) == 1
    assert resp_a_signals[0]["snippet"] == "User A secret signal"
    assert len(resp_a_actions) == 1
    assert resp_a_actions[0]["description"] == "User A secret action"

    # Assert User B only sees User B's data
    assert len(resp_b_signals) == 1
    assert resp_b_signals[0]["snippet"] == "User B secret signal"
    assert len(resp_b_actions) == 1
    assert resp_b_actions[0]["description"] == "User B secret action"
