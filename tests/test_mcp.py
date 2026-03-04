import base64
import json
import os
import pytest
import pytest_asyncio
import respx
import httpx
from httpx import AsyncClient, ASGITransport
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from unittest.mock import patch

# Set env vars before importing app
TEST_API_KEY = "test-api-key-mcp"
TEST_ENC_KEY = base64.b64encode(AESGCM.generate_key(256)).decode()

os.environ["LOCKER_API_KEY"] = TEST_API_KEY
os.environ["LOCKER_ENCRYPTION_KEY"] = TEST_ENC_KEY
os.environ["LOCKER_DB_PATH"] = ":memory:"
os.environ["ANTHROPIC_API_KEY"] = "test-anthropic-key"

from main import app  # noqa: E402
from vault.db import init_db, close_db  # noqa: E402
from locker_mcp import token_store  # noqa: E402

FAKE_ANTHROPIC_RESPONSE = {
    "id": "msg_test",
    "type": "message",
    "role": "assistant",
    "content": [{"type": "text", "text": "ok"}],
    "model": "claude-opus-4-6",
    "stop_reason": "end_turn",
    "usage": {"input_tokens": 10, "output_tokens": 5},
}


@pytest_asyncio.fixture
async def client():
    await init_db()
    token_store._clear()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
    await close_db()
    token_store._clear()


async def _create_skill(client, name: str, content: str) -> str:
    headers = {"X-API-Key": os.environ["LOCKER_API_KEY"]}
    r = await client.post(
        "/api/v1/skills",
        json={"name": name, "content": content},
        headers=headers,
    )
    assert r.status_code == 201
    return r.json()["id"]


def _mock_anthropic():
    return respx.post("https://api.anthropic.com/v1/messages").mock(
        return_value=httpx.Response(200, json=FAKE_ANTHROPIC_RESPONSE)
    )


# --- Token store unit tests ---


def test_token_registers_and_consumed_once():
    token_store._clear()
    token_store.register("tok-unit-1", "bullets")
    assert token_store.consume("tok-unit-1") == "bullets"


def test_token_is_single_use():
    token_store._clear()
    token_store.register("tok-unit-2", "bullets")
    token_store.consume("tok-unit-2")
    assert token_store.consume("tok-unit-2") is None


def test_expired_token_returns_none():
    token_store._clear()
    with patch("locker_mcp.token_store.time") as mock_time:
        mock_time.time.return_value = 1000.0
        token_store.register("tok-unit-3", "bullets")
        # Advance past TTL
        mock_time.time.return_value = 1000.0 + token_store.TTL + 1
        assert token_store.consume("tok-unit-3") is None


# --- /internal/register-token endpoint tests ---


# Fixed UUID-format tokens for endpoint and proxy tests
TOKEN_EP_1 = "aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa"
TOKEN_EP_2 = "bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbbb"
TOKEN_PROXY_1 = "cccccccc-cccc-4ccc-cccc-cccccccccccc"
TOKEN_PROXY_2 = "dddddddd-dddd-4ddd-dddd-dddddddddddd"
TOKEN_UNKNOWN = "00000000-0000-0000-0000-000000000000"


@pytest.mark.asyncio
async def test_register_token_valid(client):
    r = await client.post(
        "/internal/register-token",
        json={"token": TOKEN_EP_1, "skill_name": "bullets"},
        headers={"X-API-Key": os.environ["LOCKER_API_KEY"]},
    )
    assert r.status_code == 200
    assert r.json() == {"ok": True}
    # Token is now in the store
    assert token_store.consume(TOKEN_EP_1) == "bullets"


@pytest.mark.asyncio
async def test_register_token_no_auth(client):
    r = await client.post(
        "/internal/register-token",
        json={"token": TOKEN_EP_2, "skill_name": "bullets"},
    )
    assert r.status_code == 401


# --- Proxy token injection tests ---


@pytest.mark.asyncio
async def test_proxy_injects_skill_for_valid_token(client):
    await _create_skill(client, "bullets", "Always use bullet points.")
    token_store.register(TOKEN_PROXY_1, "bullets")

    payload = {
        "model": "claude-opus-4-6",
        "messages": [
            {"role": "user", "content": f"Help me. [LOCKER_TOKEN:{TOKEN_PROXY_1}]"}
        ],
        "max_tokens": 100,
    }
    with respx.mock:
        route = _mock_anthropic()
        r = await client.post("/proxy/anthropic/v1/messages", json=payload)
        assert r.status_code == 200
        forwarded_body = json.loads(route.calls[0].request.content)

    assert "[SKILL: bullets]" in forwarded_body["system"]
    assert "Always use bullet points." in forwarded_body["system"]
    assert "[/SKILL]" in forwarded_body["system"]


@pytest.mark.asyncio
async def test_proxy_strips_token_from_forwarded_body(client):
    await _create_skill(client, "strip-skill", "Strip test content.")
    token_store.register(TOKEN_PROXY_2, "strip-skill")

    payload = {
        "model": "claude-opus-4-6",
        "messages": [
            {"role": "user", "content": f"Do the thing [LOCKER_TOKEN:{TOKEN_PROXY_2}]"}
        ],
        "max_tokens": 100,
    }
    with respx.mock:
        route = _mock_anthropic()
        r = await client.post("/proxy/anthropic/v1/messages", json=payload)
        assert r.status_code == 200
        forwarded_body = json.loads(route.calls[0].request.content)

    assert "LOCKER_TOKEN" not in json.dumps(forwarded_body)


@pytest.mark.asyncio
async def test_proxy_unknown_token_returns_422(client):
    payload = {
        "model": "claude-opus-4-6",
        "messages": [
            {
                "role": "user",
                "content": f"[LOCKER_TOKEN:{TOKEN_UNKNOWN}]",
            }
        ],
        "max_tokens": 100,
    }
    r = await client.post("/proxy/anthropic/v1/messages", json=payload)
    assert r.status_code == 422
