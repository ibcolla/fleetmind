"""
FleetMind Phase 2 — Test Fixtures and Helpers
----------------------------------------------
Provides shared fixtures for authentication & database workspace tests.

SANDBOX CONSTRAINT:
  mem0's setup.py calls `os.makedirs(~/.mem0)` at import time. In the test
  sandbox, the home directory is read-only, so this fails. We patch mem0 in
  sys.modules BEFORE importing main.py so the app can be loaded for testing.
"""

import os
import sys
import time
import uuid
from unittest.mock import MagicMock, AsyncMock, patch

import pytest
from jose import jwt

# ─────────────────────────────────────────────────────────────────────────────
# Test-only JWT secret — NEVER use this in production
# ─────────────────────────────────────────────────────────────────────────────
TEST_JWT_SECRET = "fleetmind-test-secret-do-not-use-in-production-32chars+"
TEST_ALGORITHM = "HS256"
TEST_AUDIENCE = "authenticated"


def make_jwt(
    user_id: str = None,
    email: str = "test@example.com",
    role: str = "authenticated",
    exp_offset: int = 3600,
    secret: str = TEST_JWT_SECRET,
    audience: str = TEST_AUDIENCE,
) -> str:
    """Generate a test JWT signed with TEST_JWT_SECRET."""
    if user_id is None:
        user_id = str(uuid.uuid4())

    now = int(time.time())
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "aud": audience,
        "iat": now,
        "exp": now + exp_offset,
    }
    return jwt.encode(payload, secret, algorithm=TEST_ALGORITHM)


def auth_header(token: str) -> dict:
    """Return Authorization header dict for a given JWT."""
    return {"Authorization": f"Bearer {token}"}


# ─────────────────────────────────────────────────────────────────────────────
# Environment patching — happens at module import time, before any app import
# ─────────────────────────────────────────────────────────────────────────────

os.environ["SUPABASE_JWT_SECRET"] = TEST_JWT_SECRET
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:3000")
os.environ.setdefault("MEM0_API_KEY", "test-mem0-key")
os.environ.setdefault("NEBIUS_API_KEY", "test-nebius-key")
os.environ.setdefault("TAVILY_API_KEY", "test-tavily-key")
os.environ.setdefault("COMPOSIO_API_KEY", "test-composio-key")
os.environ.setdefault("SUPABASE_URL", "https://test-project.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")

# ─────────────────────────────────────────────────────────────────────────────
# Patch mem0 in sys.modules BEFORE any app import
# ─────────────────────────────────────────────────────────────────────────────
_mem0_mock = MagicMock()
_mem0_mock.MemoryClient = MagicMock(return_value=MagicMock(
    search=MagicMock(return_value={"results": []}),
    add=MagicMock(return_value={}),
    get_all=MagicMock(return_value={"results": []}),
    delete=MagicMock(return_value={}),
))

sys.modules.setdefault("mem0", _mem0_mock)
sys.modules.setdefault("mem0.client", MagicMock())
sys.modules.setdefault("mem0.client.main", MagicMock())
sys.modules.setdefault("mem0.memory", MagicMock())
sys.modules.setdefault("mem0.memory.setup", MagicMock())

# Patch supabase in sys.modules if not installed yet or to ensure clean mock
try:
    import supabase
except ImportError:
    mock_supabase_mod = MagicMock()
    sys.modules["supabase"] = mock_supabase_mod


from tests.mock_db import MockSupabaseClient


# ─────────────────────────────────────────────────────────────────────────────
# DB Fixture & TestClient
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_db():
    """Returns a fresh MockSupabaseClient instance per test."""
    return MockSupabaseClient()


@pytest.fixture(scope="session")
def session_mock_db():
    return MockSupabaseClient()


@pytest.fixture(scope="session")
def client(session_mock_db):
    """
    TestClient for the FleetMind FastAPI app.
    Session-scoped — app is created once, with get_db overridden to yield mock DB.
    """
    from fastapi.testclient import TestClient
    from main import app
    from api.db import get_db

    async def _override_get_db():
        yield session_mock_db

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def reset_mock_db(session_mock_db):
    """Clear mock database tables before each test to ensure isolation."""
    session_mock_db.clear()


# ─────────────────────────────────────────────────────────────────────────────
# User fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def user_a_id() -> str:
    return str(uuid.uuid4())


@pytest.fixture
def user_b_id() -> str:
    return str(uuid.uuid4())


@pytest.fixture
def token_a(user_a_id) -> str:
    return make_jwt(user_id=user_a_id, email="user_a@example.com")


@pytest.fixture
def token_b(user_b_id) -> str:
    return make_jwt(user_id=user_b_id, email="user_b@example.com")
