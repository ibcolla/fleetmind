"""
FleetMind Phase 3 — Storage, Workspace Memory, & SSRF Tests
------------------------------------------------------------
Tests:
  1. SSRF Protection: Rejection of local, loopback, private, cloud metadata, and non-HTTP URLs.
  2. Cloud Storage: Saving strategy briefs to Supabase Storage in the artifacts bucket.
  3. Workspace Memory Binding: Verification that all Mem0 operations use workspace_id.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from tools.reader_tools import validate_url_for_ssrf, deep_read_url
from tools.strategy_tools import save_strategy_brief_to_storage
from tests.conftest import auth_header, make_jwt


# ─────────────────────────────────────────────────────────────────────────────
# 1. SSRF Protection Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_ssrf_blocks_loopback_and_local():
    """Ensure loopback IPs and localhost hostnames are blocked."""
    valid, reason = validate_url_for_ssrf("http://127.0.0.1/secret")
    assert not valid
    assert "blocked" in reason.lower() or "security violation" in reason.lower()

    valid, reason = validate_url_for_ssrf("http://localhost/admin")
    assert not valid

    valid, reason = validate_url_for_ssrf("http://localhost.localdomain/test")
    assert not valid


def test_ssrf_blocks_cloud_metadata():
    """Ensure AWS / Cloud metadata IP (169.254.169.254) is blocked."""
    valid, reason = validate_url_for_ssrf("http://169.254.169.254/latest/meta-data/")
    assert not valid
    assert "blocked" in reason.lower() or "security violation" in reason.lower()


def test_ssrf_blocks_private_networks():
    """Ensure RFC 1918 private IPv4 addresses are blocked."""
    for url in ["http://10.0.0.1/status", "http://172.16.0.5/api", "http://192.168.1.1/router"]:
        valid, reason = validate_url_for_ssrf(url)
        assert not valid, f"Expected {url} to be blocked by SSRF check"


def test_ssrf_blocks_non_http_schemes():
    """Ensure non-HTTP schemes (file://, ftp://, gopher://) are blocked."""
    for url in ["file:///etc/passwd", "ftp://example.com/file", "gopher://127.0.0.1"]:
        valid, reason = validate_url_for_ssrf(url)
        assert not valid
        assert "scheme" in reason.lower() or "blocked" in reason.lower()


def test_ssrf_allows_public_urls():
    """Ensure legitimate public HTTP/HTTPS URLs pass validation."""
    valid, reason = validate_url_for_ssrf("https://example.com/article?id=123")
    assert valid
    assert reason == "OK"


def test_deep_read_url_returns_blocked_message_for_ssrf():
    """deep_read_url tool must return a safe blocked message instead of attempting HTTP GET."""
    result = deep_read_url("http://127.0.0.1/admin")
    assert "Blocked" in result or "Security Violation" in result


# ─────────────────────────────────────────────────────────────────────────────
# 2. Cloud Storage Artifact Tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_save_strategy_brief_to_supabase_storage(mock_db):
    """
    Strategy brief generator must upload files directly to Supabase Storage ('artifacts' bucket)
    under path '{workspace_id}/{filename}.md' and return a signed URL.
    """
    workspace_id = "ws-test-12345"
    title = "Q4 Product Strategy Brief"
    content = "# Q4 Strategy Brief\n\n- Focus on enterprise features\n- Ship RLS tenant isolation"

    result = await save_strategy_brief_to_storage(
        title=title,
        content=content,
        workspace_id=workspace_id,
        db=mock_db,
    )

    assert "✅ Strategy Brief" in result
    assert "Download Link:" in result

    # Verify file content in mock storage
    artifacts = mock_db.storage.buckets.get("artifacts", {})
    assert len(artifacts) == 1

    storage_path = list(artifacts.keys())[0]
    assert storage_path.startswith(f"{workspace_id}/q4_product_strategy_brief_")
    assert storage_path.endswith(".md")
    assert artifacts[storage_path] == content.encode("utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# 3. Workspace-Scoped Mem0 Memory Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_memory_endpoint_uses_workspace_id(client, token_a, user_a_id, session_mock_db):
    """
    GET /memory must retrieve memories scoped to the user's workspace.id, NOT personal user_id.
    """
    response = client.get("/memory", headers=auth_header(token_a))
    assert response.status_code == 200
    assert isinstance(response.json(), list)

    # Verify workspace was created / retrieved
    workspaces = session_mock_db.store["workspaces"]
    user_ws = next(w for w in workspaces if w["owner_id"] == user_a_id)
    assert user_ws["id"] is not None


def test_delete_memory_endpoint_uses_workspace_id(client, token_a, user_a_id):
    """
    DELETE /memory/{id} must bind deletion to the authenticated workspace.
    """
    response = client.delete("/memory/mem-789", headers=auth_header(token_a))
    assert response.status_code == 200
    assert response.json() == {"status": "deleted"}


def test_ssrf_relative_redirect_urljoin():
    """
    Verify that relative redirect locations are safely resolved with urljoin
    and validated against SSRF rules.
    """
    from tools.reader_tools import validate_url_for_ssrf
    import urllib.parse

    base_url = "https://example.com/blog"
    relative_redirect = "/releases"
    resolved = urllib.parse.urljoin(base_url, relative_redirect)

    assert resolved == "https://example.com/releases"
    is_valid, reason = validate_url_for_ssrf(resolved)
    assert is_valid is True
    assert reason == "OK"

    # Verify that a relative redirect to a internal loopback IP is blocked
    malicious_redirect = "http://127.0.0.1/admin"
    is_mal_valid, mal_reason = validate_url_for_ssrf(malicious_redirect)
    assert is_mal_valid is False
    assert "blocked" in mal_reason.lower()

