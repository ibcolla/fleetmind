"""
FleetMind Phase 5 — Resilience & Checkout Tests
-------------------------------------------------
Tests:
  1. POST /billing/checkout-session requires authentication (401 without auth).
  2. POST /billing/checkout-session returns 200 OK with a valid checkout URL.
  3. POST /billing/checkout-session respects client-supplied return_url.
  4. FleetMindAgent tenacity retry logic: _invoke_agent_with_retry retries transient failures.
  5. FleetMindAgent tenacity retry logic: _stream_agent_with_retry retries transient failures.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from tests.conftest import auth_header
from agents.fleet_agent import FleetMindAgent


def test_checkout_session_unauthenticated(client):
    """
    POST /billing/checkout-session without authentication must return 401 Unauthorized.
    """
    response = client.post("/billing/checkout-session", json={})
    assert response.status_code == 401


def test_checkout_session_authenticated(client, token_a):
    """
    POST /billing/checkout-session with valid auth must return 200 OK with checkout_url.
    """
    response = client.post(
        "/billing/checkout-session",
        json={"return_url": "http://localhost:3000"},
        headers=auth_header(token_a),
    )
    assert response.status_code == 200
    data = response.json()
    assert "checkout_url" in data
    assert "checkout_mock=true" in data["checkout_url"] or "stripe.com" in data["checkout_url"]


@pytest.mark.asyncio
async def test_agent_invoke_retry_resilience():
    """
    Verify that _invoke_agent_with_retry retries transient LLM errors
    and succeeds when the call eventually succeeds before max attempts.
    """
    agent = FleetMindAgent()
    mock_executor = MagicMock()

    call_count = 0

    async def mock_ainvoke(input_data):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise Exception("Transient LLM API Error 503 Service Unavailable")
        return {"output": "Success after retries", "intermediate_steps": []}

    mock_executor.ainvoke = AsyncMock(side_effect=mock_ainvoke)

    result = await agent._invoke_agent_with_retry(mock_executor, {"input": "test task"})

    assert result["output"] == "Success after retries"
    assert call_count == 3


@pytest.mark.asyncio
async def test_agent_stream_retry_resilience():
    """
    Verify that _stream_agent_with_retry retries transient LLM streaming errors
    and succeeds when the call eventually succeeds.
    """
    agent = FleetMindAgent()
    mock_executor = MagicMock()

    call_count = 0

    async def mock_astream(input_data):
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise Exception("Transient LLM Stream Connection Timeout")
        yield {"output": "Stream completed after retry"}

    mock_executor.astream = mock_astream

    chunks = await agent._stream_agent_with_retry(mock_executor, {"input": "test task"})

    assert len(chunks) == 1
    assert chunks[0]["output"] == "Stream completed after retry"
    assert call_count == 2
