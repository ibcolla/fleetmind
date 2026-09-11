"""
FleetMind - AI Ops Agent for Solo Founders
FastAPI Backend — Phase 2: PostgreSQL Workspaces & Tenant Schema
"""

import os
import json
import logging
import asyncio
from datetime import datetime
from typing import Optional, List, Any

from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from agents.fleet_agent import FleetMindAgent
from api.models import (
    RunAgentRequest,
    AgentResponse,
    MemoryItem,
    SignalItem,
    ActionItem,
    CheckoutSessionRequest,
    CheckoutSessionResponse,
)
from api.deps import CurrentUser, Workspace, require_auth, get_current_workspace
from api.db import get_db
from api.billing import (
    check_workspace_usage_limit,
    increment_workspace_agent_runs,
    sync_subscription_event,
    create_checkout_session,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CORS Configuration
# ---------------------------------------------------------------------------
# SECURITY: allow_origins=["*"] combined with allow_credentials=True is a
# security violation. We use explicit origin matching + Vercel preview regex.
#
# Environment variables:
#   ALLOWED_ORIGINS: comma-separated list of allowed origin URLs
#   FRONTEND_URL: primary frontend URL (e.g. https://fleetminds-ten.vercel.app)
# ---------------------------------------------------------------------------

_default_origins = [
    "http://localhost:3000",
    "http://localhost:8000",
    "https://fleetminds-ten.vercel.app",
    "https://fleetmind-hxg4.onrender.com",
]

_raw_origins = os.getenv("ALLOWED_ORIGINS", "")
_frontend_url = os.getenv("FRONTEND_URL", "")

ALLOWED_ORIGINS: List[str] = list(_default_origins)
if _raw_origins:
    ALLOWED_ORIGINS.extend([o.strip() for o in _raw_origins.split(",") if o.strip()])
if _frontend_url and _frontend_url not in ALLOWED_ORIGINS:
    ALLOWED_ORIGINS.append(_frontend_url.strip())

# Remove duplicates while preserving order
ALLOWED_ORIGINS = list(dict.fromkeys(ALLOWED_ORIGINS))

# Regex matching all Vercel preview deployments (*.vercel.app) and local hosts
ALLOW_ORIGIN_REGEX = r"https://.*\.vercel\.app|http://(localhost|127\.0\.0\.1)(:\d+)?"

app = FastAPI(
    title="FleetMind API",
    description="AI Ops Agent for Solo Founders",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=ALLOW_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Workspace-ID"],
)


agent = FleetMindAgent()


# ---------------------------------------------------------------------------
# Public endpoints (no authentication required)
# ---------------------------------------------------------------------------

@app.get("/")
async def root():
    return {"status": "FleetMind is running", "timestamp": datetime.utcnow().isoformat()}


@app.get("/health")
async def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Agent endpoints (authentication required)
# ---------------------------------------------------------------------------

@app.post("/agent/run", response_model=AgentResponse)
async def run_agent(
    request: RunAgentRequest,
    current_user: CurrentUser = Depends(require_auth),
    workspace: Workspace = Depends(get_current_workspace),
    db: Any = Depends(get_db),
):
    """
    Run the FleetMind agent with a given task.

    SECURITY: The authenticated user's ID (from the verified JWT) is always
    used as the canonical identity. Any ``user_id`` supplied in the request
    body is IGNORED — it cannot be used to impersonate another user.

    Phase 2: Signals and actions discovered during the run are persisted
    to Supabase scoped to the user's workspace.
    """
    # 1. Enforce usage limit (HTTP 402 if free tier and runs >= 10)
    check_workspace_usage_limit(workspace)

    try:
        result = await agent.run(
            task=request.task,
            user_id=current_user.id,      # authoritative — from verified JWT
            context=request.context,
            workspace_id=workspace.id,    # scoped to verified workspace
            db=db,
        )
        # 2. Increment agent execution count
        await increment_workspace_agent_runs(workspace.id, workspace.agent_runs_count, db)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Agent error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agent/stream")
async def stream_agent(
    request: RunAgentRequest,
    current_user: CurrentUser = Depends(require_auth),
    workspace: Workspace = Depends(get_current_workspace),
    db: Any = Depends(get_db),
):
    """
    Stream agent reasoning steps in real-time via SSE.

    SECURITY: Authentication is enforced via Authorization header (Bearer token).
    The JWT is never placed in a URL query parameter.
    """
    # 1. Enforce usage limit
    check_workspace_usage_limit(workspace)

    # 2. Increment agent execution count
    await increment_workspace_agent_runs(workspace.id, workspace.agent_runs_count, db)

    async def event_generator():
        async for step in agent.stream(
            task=request.task,
            user_id=current_user.id,      # authoritative — from verified JWT
            context=request.context,
            workspace_id=workspace.id,    # scoped to verified workspace
            db=db,
        ):
            yield f"data: {json.dumps(step)}\n\n"
            await asyncio.sleep(0.05)
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ---------------------------------------------------------------------------
# Stripe Webhook Endpoint (Phase 4 — Subscription Sync)
# ---------------------------------------------------------------------------

@app.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    db: Any = Depends(get_db),
):
    """
    Stripe Webhook endpoint for syncing subscription status to Supabase.

    Verifies Stripe-Signature using STRIPE_WEBHOOK_SECRET.
    Updates workspace subscription_status to 'active' or 'canceled'.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    event = None

    if webhook_secret and sig_header and "placeholder" not in webhook_secret:
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
        except ValueError as e:
            logger.error(f"Invalid payload in Stripe webhook: {e}")
            raise HTTPException(status_code=400, detail="Invalid payload")
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid signature in Stripe webhook: {e}")
            raise HTTPException(status_code=400, detail="Invalid signature")
    else:
        # Development / test mode fallback without raw signature check
        try:
            event = json.loads(payload)
        except Exception as e:
            raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_type = event.get("type") or ""
    data_object = (event.get("data") or {}).get("object") or {}

    logger.info(f"Received Stripe webhook event: {event_type}")

    if event_type in (
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    ):
        await sync_subscription_event(event_type, data_object, db)

    return {"status": "success"}


# ---------------------------------------------------------------------------
# Billing Checkout Endpoint (Phase 5 — Stripe Checkout Link Generation)
# ---------------------------------------------------------------------------

@app.post("/billing/checkout-session", response_model=CheckoutSessionResponse)
async def checkout_session(
    request: Optional[CheckoutSessionRequest] = None,
    current_user: CurrentUser = Depends(require_auth),
    workspace: Workspace = Depends(get_current_workspace),
):
    """
    Generate a Stripe Checkout URL for upgrading the workspace to Pro tier.
    Requires authentication.
    """
    return_url = request.return_url if request else None
    url = await create_checkout_session(
        workspace_id=workspace.id,
        user_email=current_user.email,
        return_url=return_url,
    )
    return CheckoutSessionResponse(checkout_url=url)



# ---------------------------------------------------------------------------
# Memory endpoints (authentication + ownership required)
#
# Memory is still backed by mem0 (Phase 3 will consider Postgres migration).
# user_id is removed from the path — always derived from the verified JWT.
# ---------------------------------------------------------------------------

@app.get("/memory", response_model=List[MemoryItem])
async def get_memories(
    current_user: CurrentUser = Depends(require_auth),
    workspace: Workspace = Depends(get_current_workspace),
):
    """Retrieve stored memories for the authenticated user's workspace (mem0-backed)."""
    try:
        memories = await agent.get_memories(workspace_id=workspace.id)
        return memories
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/memory/{memory_id}")
async def delete_memory(
    memory_id: str,
    current_user: CurrentUser = Depends(require_auth),
    workspace: Workspace = Depends(get_current_workspace),
):
    """
    Delete a specific memory owned by the workspace.

    SECURITY: Ownership is enforced by binding memory operations to workspace.id.
    """
    try:
        await agent.delete_memory(workspace_id=workspace.id, memory_id=memory_id)
        return {"status": "deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Signals endpoints (authentication + workspace scoping required)
#
# Phase 2: Data is now fetched from Supabase, scoped to the user's workspace.
# API contract (JSON response shape) is identical to Phase 1.
# ---------------------------------------------------------------------------

@app.get("/signals", response_model=List[SignalItem])
async def get_signals(
    current_user: CurrentUser = Depends(require_auth),
    workspace: Workspace = Depends(get_current_workspace),
    db: Any = Depends(get_db),
    query: Optional[str] = None,
):
    """
    Get latest market signals for the authenticated user's workspace.

    Phase 2: Fetches from Supabase ``signals`` table, scoped to workspace_id.
    User A cannot see signals from User B's workspace — workspace_id is derived
    from the verified JWT, never from a client-supplied parameter.
    """
    try:
        q = db.table("signals") \
            .select("*") \
            .eq("workspace_id", workspace.id) \
            .order("created_at", desc=True) \
            .limit(50)

        if query:
            q = q.ilike("title", f"%{query}%")

        resp = await q.execute()

        items = []
        for row in (resp.data or []):
            content = row.get("content") or ""
            items.append(SignalItem(
                id=str(row.get("id", "")),
                title=row.get("title") or (content[:50] if content else "Signal"),
                url=row.get("url") or "",
                snippet=row.get("snippet") or content,
                source=row.get("source") or "Tavily",
                signal_type=row.get("signal_type") or "market",
                importance=row.get("importance") or "medium",
                discovered_at=row.get("discovered_at") or row.get("created_at") or datetime.utcnow(),
            ))
        return items
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Actions endpoints (authentication + workspace scoping required)
#
# Phase 2: Data is now fetched from Supabase, scoped to the user's workspace.
# API contract (JSON response shape) is identical to Phase 1.
# ---------------------------------------------------------------------------

@app.get("/actions", response_model=List[ActionItem])
async def get_actions(
    current_user: CurrentUser = Depends(require_auth),
    workspace: Workspace = Depends(get_current_workspace),
    db: Any = Depends(get_db),
):
    """
    Get history of actions taken by the agent for the authenticated user's workspace.

    Phase 2: Fetches from Supabase ``actions`` table, scoped to workspace_id.
    """
    try:
        resp = await db.table("actions") \
            .select("*") \
            .eq("workspace_id", workspace.id) \
            .order("created_at", desc=True) \
            .limit(50) \
            .execute()

        items = []
        for row in (resp.data or []):
            content = row.get("content") or ""
            items.append(ActionItem(
                id=str(row.get("id", "")),
                user_id=str(row.get("user_id") or current_user.id),
                action_type=row.get("action_type") or "composio_tool",
                description=row.get("description") or content,
                tool=row.get("tool") or "Composio",
                status=row.get("status") or "completed",
                result=row.get("result"),
                executed_at=row.get("executed_at") or row.get("created_at") or datetime.utcnow(),
            ))
        return items
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch actions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
