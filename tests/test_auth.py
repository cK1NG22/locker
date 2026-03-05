import base64
import os
from datetime import datetime, timezone
from unittest.mock import patch

import jwt as _jwt
import pytest
import pytest_asyncio
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from httpx import AsyncClient, ASGITransport

TEST_JWT_SECRET = "test-jwt-secret"
TEST_ENC_KEY = base64.b64encode(AESGCM.generate_key(256)).decode()

os.environ["LOCKER_JWT_SECRET"] = TEST_JWT_SECRET
os.environ["LOCKER_ENCRYPTION_KEY"] = TEST_ENC_KEY
os.environ["LOCKER_DB_PATH"] = ":memory:"
os.environ["GOOGLE_CLIENT_ID"] = "test-client-id.apps.googleusercontent.com"

from main import app  # noqa: E402
from vault.db import init_db, close_db  # noqa: E402


def _make_jwt(secret: str = TEST_JWT_SECRET, exp_year: int = 2099) -> str:
    payload = {
        "sub": "test-user-id",
        "email": "test@example.com",
        "exp": datetime(exp_year, 1, 1, tzinfo=timezone.utc),
    }
    return _jwt.encode(payload, secret, algorithm="HS256")


@pytest_asyncio.fixture
async def client():
    await init_db()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
    await close_db()


# --- JWT validation ---

@pytest.mark.asyncio
async def test_valid_jwt_allows_access(client):
    token = _make_jwt()
    r = await client.get("/api/v1/skills", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_missing_auth_header_returns_401(client):
    r = await client.get("/api/v1/skills")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_invalid_token_returns_401(client):
    r = await client.get("/api/v1/skills", headers={"Authorization": "Bearer not-a-real-token"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_wrong_secret_returns_401(client):
    token = _make_jwt(secret="wrong-secret")
    r = await client.get("/api/v1/skills", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_expired_token_returns_401(client):
    token = _make_jwt(exp_year=2000)  # already expired
    r = await client.get("/api/v1/skills", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


# --- Google OAuth endpoint ---

@pytest.mark.asyncio
async def test_google_login_creates_user_and_returns_jwt(client):
    fake_idinfo = {
        "sub": "google-user-123",
        "email": "user@example.com",
        "name": "Test User",
    }
    with patch("src.auth.oauth.id_token.verify_oauth2_token", return_value=fake_idinfo):
        r = await client.post(
            "/api/v1/auth/google",
            json={"token": "fake-google-token"},
        )
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert data["user"]["email"] == "user@example.com"
    assert data["user"]["name"] == "Test User"
    # Verify the returned JWT is valid
    decoded = _jwt.decode(data["access_token"], TEST_JWT_SECRET, algorithms=["HS256"])
    assert decoded["email"] == "user@example.com"


@pytest.mark.asyncio
async def test_google_login_upserts_existing_user(client):
    fake_idinfo = {
        "sub": "google-user-456",
        "email": "returning@example.com",
        "name": "Old Name",
    }
    with patch("src.auth.oauth.id_token.verify_oauth2_token", return_value=fake_idinfo):
        r1 = await client.post("/api/v1/auth/google", json={"token": "fake-token"})
    user_id_1 = r1.json()["user"]["id"]

    fake_idinfo["name"] = "New Name"
    with patch("src.auth.oauth.id_token.verify_oauth2_token", return_value=fake_idinfo):
        r2 = await client.post("/api/v1/auth/google", json={"token": "fake-token"})
    user_id_2 = r2.json()["user"]["id"]

    # Same user ID (upserted), updated name
    assert user_id_1 == user_id_2
    assert r2.json()["user"]["name"] == "New Name"


@pytest.mark.asyncio
async def test_google_login_invalid_token_returns_401(client):
    with patch(
        "src.auth.oauth.id_token.verify_oauth2_token",
        side_effect=ValueError("Token is invalid"),
    ):
        r = await client.post("/api/v1/auth/google", json={"token": "bad-token"})
    assert r.status_code == 401
