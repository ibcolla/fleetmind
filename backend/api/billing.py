"""
FleetMind — Stripe Billing & Usage Limiter Module
--------------------------------------------------
Phase 4: Billing foundation for usage limits & Stripe integration.

Core rules:
  1. Free tier workspaces are restricted to FREE_TIER_LIMIT (10) agent runs.
  2. Attempting to run/stream an agent task beyond 10 runs returns HTTP 402 Payment Required.
  3. Workspaces with subscription_status == 'active' bypass the usage limit.
  4. Stripe webhooks securely update subscription_status to 'active' or 'canceled'.
"""

import os
import logging
from typing import Any, Optional, Dict

import stripe
from fastapi import HTTPException, status

from api.deps import Workspace

logger = logging.getLogger(__name__)

# Free tier usage limit (max agent execution runs)
FREE_TIER_LIMIT = 10

# Initialize Stripe API key
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "sk_test_placeholder_key")


def check_workspace_usage_limit(workspace: Workspace) -> None:
    """
    Enforce free tier usage limit.

    Args:
        workspace: The authenticated user's workspace dataclass.

    Raises:
        HTTPException 402: If workspace is on 'free' tier and has reached limit (10 runs).
    """
    is_free_tier = (workspace.subscription_status or "free").lower() == "free"
    runs_count = workspace.agent_runs_count or 0

    if is_free_tier and runs_count >= FREE_TIER_LIMIT:
        logger.warning(
            "Workspace %s (free tier) blocked: reached usage limit (%d/%d runs).",
            workspace.id,
            runs_count,
            FREE_TIER_LIMIT,
        )
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Free tier limit reached. Please upgrade to continue using FleetMind.",
        )


async def increment_workspace_agent_runs(workspace_id: str, current_runs: int, db: Any) -> int:
    """
    Increment the agent_runs_count for a workspace in Supabase.

    Args:
        workspace_id: Workspace UUID.
        current_runs: Current runs count.
        db:           Supabase client.

    Returns:
        The new agent_runs_count integer.
    """
    new_count = current_runs + 1
    try:
        await db.table("workspaces") \
            .update({"agent_runs_count": new_count}) \
            .eq("id", workspace_id) \
            .execute()
    except Exception as exc:
        logger.warning("Failed to increment agent_runs_count for workspace %s: %s", workspace_id, exc)
    return new_count


async def sync_subscription_event(event_type: str, data_object: Dict[str, Any], db: Any) -> bool:
    """
    Process Stripe webhook events to update workspace subscription status.

    Supported events:
      - customer.subscription.created
      - customer.subscription.updated
      - customer.subscription.deleted

    Args:
        event_type: Stripe event type string.
        data_object: Event data object (subscription or customer dict).
        db: Supabase client.

    Returns:
        True if updated, False otherwise.
    """
    customer_id = data_object.get("customer")
    subscription_id = data_object.get("id")
    raw_status = (data_object.get("status") or "").lower()

    if not customer_id:
        logger.warning("Stripe event missing customer ID")
        return False

    # Map Stripe subscription status to FleetMind status
    if event_type == "customer.subscription.deleted" or raw_status in ("canceled", "unpaid"):
        target_status = "canceled"
    elif raw_status in ("active", "trialing"):
        target_status = "active"
    else:
        target_status = raw_status or "free"

    try:
        # Update by stripe_customer_id or customer metadata
        update_data = {
            "subscription_status": target_status,
            "stripe_subscription_id": subscription_id,
        }

        # Check metadata for workspace_id if present
        metadata = data_object.get("metadata") or {}
        workspace_id = metadata.get("workspace_id")

        if workspace_id:
            await db.table("workspaces") \
                .update(update_data) \
                .eq("id", workspace_id) \
                .execute()
        else:
            await db.table("workspaces") \
                .update(update_data) \
                .eq("stripe_customer_id", customer_id) \
                .execute()

        logger.info(
            "Synced Stripe subscription %s (customer=%s) status -> %s",
            subscription_id,
            customer_id,
            target_status,
        )
        return True
    except Exception as exc:
        logger.error("Failed to sync Stripe subscription event to DB: %s", exc)
        return False


async def create_checkout_session(
    workspace_id: str,
    user_email: Optional[str] = None,
    return_url: Optional[str] = None,
) -> str:
    """
    Create a Stripe Checkout Session for upgrading a Workspace to the Pro tier.

    Args:
        workspace_id: The authenticated workspace UUID.
        user_email:   The user's email address for pre-filling Stripe checkout.
        return_url:   Frontend origin URL to redirect to after checkout.

    Returns:
        The checkout URL string for client redirect.
    """
    base_url = return_url or os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")[0]

    secret_key = os.getenv("STRIPE_SECRET_KEY", "")
    if not secret_key or "placeholder" in secret_key or "sk_test_placeholder" in secret_key:
        logger.info("Using mock checkout URL for dev mode (STRIPE_SECRET_KEY not set)")
        return f"{base_url}?checkout_mock=true&workspace_id={workspace_id}"

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": "FleetMind Pro",
                        "description": "Unlimited AI Chief of Staff agent runs for your team.",
                    },
                    "unit_amount": 4900,  # $49/month
                    "recurring": {"interval": "month"},
                },
                "quantity": 1,
            }],
            customer_email=user_email,
            metadata={"workspace_id": workspace_id},
            success_url=f"{base_url}?session_id={{CHECKOUT_SESSION_ID}}&status=success",
            cancel_url=f"{base_url}?status=cancelled",
        )
        return session.url
    except Exception as exc:
        logger.error("Failed to create Stripe checkout session for workspace %s: %s", workspace_id, exc)
        return f"{base_url}?checkout_mock=true&workspace_id={workspace_id}"
