"""
FleetMind - FastAPI Authentication & Workspace Dependencies
------------------------------------------------------------
Phase 2 additions:
  - ``Workspace`` dataclass
  - ``get_current_workspace()`` — auto-provisions a workspace on first login

Phase 1 (unchanged):
  - ``CurrentUser`` dataclass
  - ``get_current_user()`` / ``require_auth`` — JWT verification dependency

Usage in a route:
    from api.deps import require_auth, get_current_workspace, CurrentUser, Workspace

    @app.get("/signals")
    async def get_signals(
        current_user: CurrentUser = Depends(require_auth),
        workspace: Workspace = Depends(get_current_workspace),
        db = Depends(get_db),
    ):
        ...

Security invariant (unchanged from Phase 1):
    ``current_user.id`` and ``workspace.id`` are derived exclusively from the
    verified JWT subject. They cannot be influenced by client-supplied request
    body or path parameters.
"""

import logging
from dataclasses import dataclass
from typing import Any, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.auth import AuthenticationError, verify_supabase_jwt
# db import is deferred inside get_current_workspace to avoid circular imports
# at module load time (db.py imports nothing from deps.py so this is safe)
from api.db import get_db

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CurrentUser — the authoritative principal (Phase 1, unchanged)
# ---------------------------------------------------------------------------

@dataclass
class CurrentUser:
    """
    The authenticated, verified identity extracted from the Supabase JWT.

    All fields come from the verified JWT — never from client-supplied params.

    Attributes:
        id:    The user's UUID (JWT ``sub`` claim). Canonical tenant identifier.
        email: The user's email address (if present in the JWT).
        role:  The Supabase role string (typically ``"authenticated"``).
    """
    id: str
    email: Optional[str] = None
    role: Optional[str] = None


# ---------------------------------------------------------------------------
# Workspace — the tenant container (Phase 2)
# ---------------------------------------------------------------------------

@dataclass
class Workspace:
    """
    The workspace that belongs to the authenticated user.

    A workspace is the top-level tenant boundary in FleetMind. Every user has
    exactly one workspace (auto-provisioned on first login).

    Attributes:
        id:                     The workspace UUID. Used to scope all DB queries.
        name:                   Human-readable name (default: "Personal Workspace").
        owner_id:               The user UUID who owns this workspace.
        stripe_customer_id:     Stripe Customer ID string (if linked).
        stripe_subscription_id: Stripe Subscription ID string (if active).
        subscription_status:    Subscription tier ('free', 'active', 'canceled').
        agent_runs_count:       Total agent execution runs completed by this workspace.
    """
    id: str
    name: str
    owner_id: str
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    subscription_status: str = "free"
    agent_runs_count: int = 0


# ---------------------------------------------------------------------------
# HTTPBearer extractor (auto_error=False for clean 401)
# ---------------------------------------------------------------------------

_bearer_scheme = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# get_current_user — Phase 1 core dependency (unchanged)
# ---------------------------------------------------------------------------

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> CurrentUser:
    """
    FastAPI dependency that extracts and verifies the Supabase JWT from the
    ``Authorization: Bearer <token>`` header.

    Returns:
        A ``CurrentUser`` whose ``id`` is the authoritative user UUID.

    Raises:
        HTTPException 401: If the token is absent, invalid, or expired.
    """
    _unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Provide a valid Bearer token.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise _unauthorized

    try:
        payload = verify_supabase_jwt(credentials.credentials)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: Optional[str] = payload.get("sub")
    if not user_id:
        raise _unauthorized

    return CurrentUser(
        id=user_id,
        email=payload.get("email"),
        role=payload.get("role"),
    )


# ---------------------------------------------------------------------------
# get_current_workspace — Phase 2 & 4 dependency (auto-provisioning + billing)
# ---------------------------------------------------------------------------

async def get_current_workspace(
    current_user: CurrentUser = Depends(get_current_user),
    db: Any = Depends(get_db),
) -> Workspace:
    """
    FastAPI dependency that resolves (or creates) the authenticated user's
    workspace.
    """
    try:
        # 1. Look up existing workspace for this user
        resp = await db.table("workspaces") \
            .select("id, name, owner_id, stripe_customer_id, stripe_subscription_id, subscription_status, agent_runs_count") \
            .eq("owner_id", current_user.id) \
            .limit(1) \
            .execute()

        if resp.data:
            row = resp.data[0]
            return Workspace(
                id=row["id"],
                name=row["name"],
                owner_id=row["owner_id"],
                stripe_customer_id=row.get("stripe_customer_id"),
                stripe_subscription_id=row.get("stripe_subscription_id"),
                subscription_status=row.get("subscription_status") or "free",
                agent_runs_count=row.get("agent_runs_count") or 0,
            )

        # 2. Auto-provision: create workspace + membership (first login)
        logger.info(
            "Auto-provisioning workspace for new user %s", current_user.id
        )

        ws_resp = await db.table("workspaces").insert({
            "name": "Personal Workspace",
            "owner_id": current_user.id,
            "subscription_status": "free",
            "agent_runs_count": 0,
        }).execute()

        if not ws_resp.data:
            raise RuntimeError("Workspace INSERT returned no data.")

        workspace_row = ws_resp.data[0]
        workspace_id = workspace_row["id"]

        # 3. Create workspace_users membership record
        await db.table("workspace_users").insert({
            "workspace_id": workspace_id,
            "user_id": current_user.id,
            "role": "owner",
        }).execute()

        return Workspace(
            id=workspace_id,
            name=workspace_row["name"],
            owner_id=workspace_row["owner_id"],
            stripe_customer_id=workspace_row.get("stripe_customer_id"),
            stripe_subscription_id=workspace_row.get("stripe_subscription_id"),
            subscription_status=workspace_row.get("subscription_status") or "free",
            agent_runs_count=workspace_row.get("agent_runs_count") or 0,
        )

    except HTTPException:
        raise  # 503 from get_db bubbles up unchanged

    except Exception as exc:
        logger.error(
            "Workspace resolution failed for user %s: %s", current_user.id, exc
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resolve workspace. Please try again.",
        )


# ---------------------------------------------------------------------------
# Convenience aliases
# ---------------------------------------------------------------------------

#: Alias for ``get_current_user`` — use in routes for clarity:
#:   ``current_user: CurrentUser = Depends(require_auth)``
require_auth = get_current_user
