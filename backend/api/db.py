"""
FleetMind — Supabase Database Client
-------------------------------------
Initialises a singleton async Supabase client using the SERVICE ROLE KEY.

Security model
--------------
We use the service-role key (which bypasses Postgres RLS) because:
  1. The calling user's identity has already been verified by the JWT layer
     (api/auth.py + api/deps.py) before any DB call is made.
  2. The workspace_id used in every query is derived from the verified JWT
     subject — it is never accepted from client-supplied input.
  3. RLS still provides defence-in-depth for any direct Supabase API calls
     (e.g. from Supabase Studio or a future anon client).

The service-role key must NEVER be exposed to the browser or frontend.

Configuration
-------------
Set in backend/.env:
    SUPABASE_URL=https://your-project-ref.supabase.co
    SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

Usage (in a FastAPI route)
--------------------------
    from api.db import get_db
    from supabase import AsyncClient

    @app.get("/example")
    async def example(db: AsyncClient = Depends(get_db)):
        resp = await db.table("signals").select("*").execute()
        return resp.data
"""

import logging
import os
from typing import AsyncGenerator, Optional

from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy singleton — created on first request, reused thereafter
# ---------------------------------------------------------------------------
_supabase_client = None
_supabase_available: bool = True  # set False if env vars are missing


async def _get_client():
    """
    Return the singleton async Supabase client, creating it on first call.

    Raises:
        RuntimeError: If SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY are not set.
    """
    global _supabase_client, _supabase_available

    if not _supabase_available:
        raise RuntimeError("Supabase client is not configured (missing env vars).")

    if _supabase_client is not None:
        return _supabase_client

    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()

    if not url or not key or "your-project-ref" in url or "your-service-role" in key:
        _supabase_available = False
        logger.warning(
            "SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not configured. "
            "Database endpoints will return HTTP 503 until these are set."
        )
        raise RuntimeError(
            "Supabase is not configured. "
            "Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in backend/.env."
        )

    try:
        from supabase import acreate_client, AsyncClient  # type: ignore
        _supabase_client = await acreate_client(url, key)
        logger.info("Supabase async client initialised.")
        return _supabase_client
    except Exception as exc:
        _supabase_available = False
        logger.error(f"Failed to initialise Supabase client: {exc}")
        raise RuntimeError(f"Supabase client initialisation failed: {exc}") from exc


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

async def get_db():
    """
    FastAPI dependency that yields the singleton Supabase async client.

    Raises:
        HTTPException 503: If Supabase is not configured or unavailable.
    """
    try:
        client = await _get_client()
        yield client
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database unavailable: {exc}",
        )


# ---------------------------------------------------------------------------
# Utility: reset client (for testing / hot-reload)
# ---------------------------------------------------------------------------

def reset_client(available: Optional[bool] = None) -> None:
    """
    Reset the singleton client. Used in tests to inject a mock client.

    Args:
        available: Override the _supabase_available flag. Pass True when
                   injecting a mock so get_db() skips the real init.
    """
    global _supabase_client, _supabase_available
    _supabase_client = None
    if available is not None:
        _supabase_available = available
    else:
        _supabase_available = True
