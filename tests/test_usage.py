import base64
import os
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Generate test keys before app is imported
TEST_API_KEY = "test-api-key-1234"
TEST_ENC_KEY = base64.b64encode(AESGCM.generate_key(256)).decode()

os.environ["LOCKER_API_KEY"] = TEST_API_KEY
os.environ["LOCKER_ENCRYPTION_KEY"] = TEST_ENC_KEY
os.environ["LOCKER_DB_PATH"] = ":memory:"

from main import app  # noqa: E402
from vault.db import init_db, close_db, get_db  # noqa: E402
from vault.usage import log_usage  # noqa: E402

HEADERS = {"X-API-Key": TEST_API_KEY}


@pytest_asyncio.fixture
async def client():
    await init_db()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
    await close_db()


# --- Empty state ---

@pytest.mark.asyncio
async def test_usage_empty(client):
    r = await client.get("/api/v1/usage", headers=HEADERS)
    assert r.status_code == 200
    assert r.json() == {"usage": []}


# --- Log and retrieve ---

@pytest.mark.asyncio
async def test_log_and_get_usage(client):
    # Create a skill via API
    await client.post(
        "/api/v1/skills",
        json={"name": "tracked-skill", "content": "Do the thing."},
        headers=HEADERS,
    )

    # Mock the Anthropic API call so the proxy doesn't make a real request
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.content = b'{"content": [{"type": "text", "text": "hello"}]}'
    mock_response.headers = {"content-type": "application/json"}

    with patch("proxy.routes.httpx.AsyncClient") as mock_client_cls:
        mock_http = AsyncMock()
        mock_http.post.return_value = mock_response
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_http

        os.environ["ANTHROPIC_API_KEY"] = "fake-key"
        await client.post(
            "/proxy/anthropic/v1/messages",
            json={
                "model": "claude-sonnet-4-20250514",
                "messages": [
                    {"role": "user", "content": "/locker tracked-skill\nHello"}
                ],
            },
        )

    r = await client.get("/api/v1/usage", headers=HEADERS)
    assert r.status_code == 200
    usage = r.json()["usage"]
    assert len(usage) == 1
    assert usage[0]["skill_name"] == "tracked-skill"
    assert usage[0]["source"] == "proxy"


# --- Filter by skill_name ---

@pytest.mark.asyncio
async def test_usage_filter_by_skill_name(client):
    db = get_db()
    await log_usage(db, "skill-a", None, "proxy")
    await log_usage(db, "skill-b", None, "mcp")

    r = await client.get("/api/v1/usage?skill_name=skill-a", headers=HEADERS)
    assert r.status_code == 200
    usage = r.json()["usage"]
    assert len(usage) == 1
    assert usage[0]["skill_name"] == "skill-a"


# --- Summary ---

@pytest.mark.asyncio
async def test_usage_summary(client):
    db = get_db()
    await log_usage(db, "popular", None, "proxy")
    await log_usage(db, "popular", None, "mcp")
    await log_usage(db, "popular", None, "proxy")
    await log_usage(db, "rare", None, "sync")

    r = await client.get("/api/v1/usage/summary", headers=HEADERS)
    assert r.status_code == 200
    summary = r.json()["summary"]
    by_name = {s["skill_name"]: s["count"] for s in summary}
    assert by_name["popular"] == 3
    assert by_name["rare"] == 1


# --- Auth required ---

@pytest.mark.asyncio
async def test_usage_requires_auth(client):
    r = await client.get("/api/v1/usage")
    assert r.status_code == 401

    r2 = await client.get("/api/v1/usage/summary")
    assert r2.status_code == 401
