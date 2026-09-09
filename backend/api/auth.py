"""
FleetMind - Supabase JWT Verification
--------------------------------------
Verifies JWTs issued by Supabase using the project's JWT secret (HS256).
No service-role key is required for verification — only the JWT secret from
Supabase project settings → API → JWT Secret.

The JWT secret MUST remain server-side only (backend/.env).
It must NEVER be exposed to the frontend or browser.
"""

import os
import logging
from typing import Optional

from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SUPABASE_JWT_SECRET: Optional[str] = os.getenv("SUPABASE_JWT_SECRET")
SUPABASE_URL: Optional[str] = os.getenv("SUPABASE_URL")

# Supabase always uses HS256 for project JWTs
_JWT_ALGORITHM = "HS256"

# Supabase sets the audience to "authenticated" for logged-in users
_JWT_AUDIENCE = "authenticated"


def _is_configured() -> bool:
    """Return True if Supabase JWT verification is properly configured."""
    if not SUPABASE_JWT_SECRET:
        logger.warning(
            "SUPABASE_JWT_SECRET is not set. "
            "All protected endpoints will return 401. "
            "Set this variable in backend/.env to enable authentication."
        )
        return False
    return True


def verify_supabase_jwt(token: str) -> dict:
    """
    Decode and verify a Supabase-issued JWT.

    Args:
        token: Raw JWT string (without the 'Bearer ' prefix).

    Returns:
        The decoded JWT payload dict. Key fields:
          - ``sub``   — the authenticated user's UUID (authoritative user_id)
          - ``email`` — user's email address
          - ``role``  — Supabase role (usually "authenticated")
          - ``exp``   — expiry timestamp

    Raises:
        AuthenticationError: If the token is missing, invalid, or expired.
    """
    if not _is_configured():
        raise AuthenticationError("Authentication service is not configured.")

    if not token or not token.strip():
        raise AuthenticationError("No token provided.")

    try:
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=[_JWT_ALGORITHM],
            audience=_JWT_AUDIENCE,
            options={
                "verify_exp": True,
                "verify_aud": True,
            },
        )
        return payload

    except ExpiredSignatureError:
        raise AuthenticationError("Token has expired. Please sign in again.")
    except JWTError as exc:
        logger.debug("JWT verification failed: %s", exc)
        raise AuthenticationError("Invalid token.")


class AuthenticationError(Exception):
    """Raised when JWT verification fails for any reason."""
    pass
