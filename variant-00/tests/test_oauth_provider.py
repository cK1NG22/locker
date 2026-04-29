"""Tests for the OAuth 2.1 provider."""

import time
import uuid
from datetime import datetime, timezone

import pytest
from pydantic import AnyUrl

from mcp.server.auth.provider import AuthorizationParams
from mcp.shared.auth import OAuthClientInformationFull

from locker_mcp.oauth_provider import (
    ACCESS_TOKEN_TTL,
    LockerOAuthProvider,
)
from vault.db import get_db, init_db, close_db


@pytest.fixture
async def provider(pg_container):
    await init_db()
    yield LockerOAuthProvider()
    await close_db()


def _make_client_info(client_id: str = "test-client") -> OAuthClientInformationFull:
    return OAuthClientInformationFull(
        client_id=client_id,
        client_secret="test-secret-value",
        redirect_uris=[AnyUrl("https://claude.ai/api/mcp/auth_callback")],
        token_endpoint_auth_method="client_secret_post",
        grant_types=["authorization_code", "refresh_token"],
        response_types=["code"],
        scope="skills:read feedback:write",
        client_name="Test Client",
    )


# --- Client registration ---

async def test_register_and_get_client(provider):
    info = _make_client_info()
    await provider.register_client(info)
    loaded = await provider.get_client("test-client")
    assert loaded is not None
    assert loaded.client_id == "test-client"
    assert loaded.client_name == "Test Client"


async def test_get_client_not_found(provider):
    result = await provider.get_client("nonexistent")
    assert result is None


# --- Authorization ---

async def test_authorize_returns_consent_url(provider):
    info = _make_client_info()
    await provider.register_client(info)
    params = AuthorizationParams(
        state="test-state",
        scopes=["skills:read"],
        code_challenge="challenge123",
        redirect_uri=AnyUrl("https://claude.ai/api/mcp/auth_callback"),
        redirect_uri_provided_explicitly=True,
    )
    url = await provider.authorize(info, params)
    assert "/oauth/consent?session=" in url


# --- Authorization code exchange ---

async def _setup_auth_code(provider, db) -> tuple[OAuthClientInformationFull, str]:
    """Helper: register client + insert an auth code directly."""
    info = _make_client_info()
    await provider.register_client(info)

    code = "test-auth-code-" + uuid.uuid4().hex[:8]
    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        "INSERT INTO oauth_codes (code, client_id, user_id, team_id, scopes, code_challenge, "
        "redirect_uri, redirect_uri_provided_explicitly, expires_at, created_at) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)",
        code, "test-client", "user-1", "team-1", "skills:read",
        "challenge123", "https://claude.ai/api/mcp/auth_callback", True,
        time.time() + 600, now,
    )
    return info, code


async def test_load_authorization_code(provider):
    db = get_db()
    info, code = await _setup_auth_code(provider, db)
    loaded = await provider.load_authorization_code(info, code)
    assert loaded is not None
    assert loaded.code == code
    assert loaded.user_id == "user-1"
    assert loaded.team_id == "team-1"


async def test_load_authorization_code_expired(provider):
    db = get_db()
    info = _make_client_info()
    await provider.register_client(info)

    code = "expired-code"
    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        "INSERT INTO oauth_codes (code, client_id, user_id, team_id, scopes, code_challenge, "
        "redirect_uri, redirect_uri_provided_explicitly, expires_at, created_at) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)",
        code, "test-client", "user-1", "team-1", "skills:read",
        "challenge123", "https://claude.ai/api/mcp/auth_callback", True,
        time.time() - 10, now,  # already expired
    )
    loaded = await provider.load_authorization_code(info, code)
    assert loaded is None


async def test_exchange_authorization_code(provider):
    db = get_db()
    info, code_str = await _setup_auth_code(provider, db)
    auth_code = await provider.load_authorization_code(info, code_str)
    assert auth_code is not None

    token = await provider.exchange_authorization_code(info, auth_code)
    assert token.access_token
    assert token.refresh_token
    assert token.token_type == "Bearer"
    assert token.expires_in == ACCESS_TOKEN_TTL

    # Code should be deleted
    reloaded = await provider.load_authorization_code(info, code_str)
    assert reloaded is None


# --- Access token ---

async def test_load_access_token(provider):
    db = get_db()
    info, code_str = await _setup_auth_code(provider, db)
    auth_code = await provider.load_authorization_code(info, code_str)
    oauth_token = await provider.exchange_authorization_code(info, auth_code)

    loaded = await provider.load_access_token(oauth_token.access_token)
    assert loaded is not None
    assert loaded.user_id == "user-1"
    assert loaded.team_id == "team-1"
    assert loaded.client_id == "test-client"


async def test_load_access_token_not_found(provider):
    result = await provider.load_access_token("nonexistent-token")
    assert result is None


# --- Refresh token ---

async def test_load_and_exchange_refresh_token(provider):
    db = get_db()
    info, code_str = await _setup_auth_code(provider, db)
    auth_code = await provider.load_authorization_code(info, code_str)
    oauth_token = await provider.exchange_authorization_code(info, auth_code)

    refresh = await provider.load_refresh_token(info, oauth_token.refresh_token)
    assert refresh is not None
    assert refresh.user_id == "user-1"

    # Exchange refresh token
    new_token = await provider.exchange_refresh_token(info, refresh, ["skills:read"])
    assert new_token.access_token != oauth_token.access_token
    assert new_token.refresh_token != oauth_token.refresh_token

    # Old refresh token should be revoked
    old_refresh = await provider.load_refresh_token(info, oauth_token.refresh_token)
    assert old_refresh is None

    # New tokens should work
    new_access = await provider.load_access_token(new_token.access_token)
    assert new_access is not None


# --- Revocation ---

async def test_revoke_token(provider):
    db = get_db()
    info, code_str = await _setup_auth_code(provider, db)
    auth_code = await provider.load_authorization_code(info, code_str)
    oauth_token = await provider.exchange_authorization_code(info, auth_code)

    access = await provider.load_access_token(oauth_token.access_token)
    assert access is not None

    await provider.revoke_token(access)

    # Both access and refresh should be revoked
    assert await provider.load_access_token(oauth_token.access_token) is None
    assert await provider.load_refresh_token(info, oauth_token.refresh_token) is None
