"""Tests for rate limiting (task 4.5)."""

import pytest
from unittest.mock import MagicMock
from httpx import ASGITransport, AsyncClient

from src.middleware.rate_limit import get_rate_limit_key
from tests.conftest import TEST_JWT


@pytest.fixture
def client(pg_container):
    from main import app
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_auth_rate_limit_429(client):
    """Auth endpoint should return 429 after 10 requests per minute."""
    for i in range(10):
        resp = await client.post("/api/v1/auth/google", json={"token": "bad"})
        # Expect 401 (invalid token) or similar, but not 429 yet
        assert resp.status_code != 429, f"Got 429 too early on request {i+1}"

    # 11th request should be rate limited
    resp = await client.post("/api/v1/auth/google", json={"token": "bad"})
    assert resp.status_code == 429


@pytest.mark.asyncio
async def test_429_has_retry_after_header(client):
    """429 response should include Retry-After header."""
    for _ in range(11):
        resp = await client.post("/api/v1/auth/google", json={"token": "bad"})
    assert resp.status_code == 429
    assert "retry-after" in resp.headers


@pytest.mark.asyncio
async def test_health_not_rate_limited(client):
    """Health endpoint should be exempt from rate limiting."""
    for _ in range(200):
        resp = await client.get("/health")
        assert resp.status_code == 200


def test_key_function_uses_jwt_sub():
    """Key function should extract JWT sub for Bearer auth."""
    request = MagicMock()
    request.headers = {"Authorization": f"Bearer {TEST_JWT}"}
    request.client = MagicMock()
    request.client.host = "127.0.0.1"

    key = get_rate_limit_key(request)
    assert key == "user:test-user-id"


def test_key_function_uses_team_token():
    """Key function should use X-Team-Token when present."""
    request = MagicMock()
    request.headers = {"X-Team-Token": "abc-123"}
    request.client = MagicMock()
    request.client.host = "127.0.0.1"

    key = get_rate_limit_key(request)
    assert key == "team:abc-123"


def test_key_function_falls_back_to_ip():
    """Key function should fall back to client IP when no auth headers."""
    request = MagicMock()
    request.headers = {}
    request.client = MagicMock()
    request.client.host = "192.168.1.1"

    key = get_rate_limit_key(request)
    assert key == "ip:192.168.1.1"
