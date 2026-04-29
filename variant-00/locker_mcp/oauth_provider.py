"""OAuth 2.1 Authorization Server Provider for Locker MCP.

Implements the 9-method OAuthAuthorizationServerProvider protocol from the MCP SDK.
Stores clients, codes, and tokens in Postgres. Tokens are opaque hex strings,
stored as SHA-256 hashes (same pattern as team tokens).
"""

import json
import os
import secrets
import time
from datetime import datetime, timezone

import jwt as pyjwt
from pydantic import AnyUrl

from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    RefreshToken,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken

from vault.db import get_db
from vault.token_utils import hash_token


def _parse_scopes(scopes_str: str) -> list[str]:
    """Split space-separated scopes, handling empty string correctly."""
    return scopes_str.split(" ") if scopes_str else []

# TTLs
ACCESS_TOKEN_TTL = 3600  # 1 hour
REFRESH_TOKEN_TTL = 30 * 24 * 3600  # 30 days
AUTH_CODE_TTL = 600  # 10 minutes


# --- Custom subclasses with user_id + team_id ---

class LockerAuthorizationCode(AuthorizationCode):
    user_id: str
    team_id: str


class LockerAccessToken(AccessToken):
    user_id: str
    team_id: str


class LockerRefreshToken(RefreshToken):
    user_id: str
    team_id: str


def _jwt_secret() -> str:
    return os.environ.get("LOCKER_JWT_SECRET", "dev-secret-change-me")


def _generate_opaque_token() -> str:
    """Generate a 32-byte hex token (256 bits of entropy)."""
    return secrets.token_hex(32)


class LockerOAuthProvider:
    """OAuth 2.1 provider backed by Postgres."""

    # --- Client registration (DCR) ---

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        db = get_db()
        row = await db.fetchrow(
            "SELECT client_info_json FROM oauth_clients WHERE client_id = $1",
            client_id,
        )
        if row is None:
            return None
        return OAuthClientInformationFull(**json.loads(row["client_info_json"]))

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        db = get_db()
        now = datetime.now(timezone.utc).isoformat()
        secret_hash = hash_token(client_info.client_secret) if client_info.client_secret else None
        await db.execute(
            "INSERT INTO oauth_clients (client_id, client_secret_hash, client_info_json, created_at) "
            "VALUES ($1, $2, $3, $4)",
            client_info.client_id,
            secret_hash,
            client_info.model_dump_json(),
            now,
        )

    # --- Authorization ---

    async def authorize(
        self,
        client: OAuthClientInformationFull,
        params: AuthorizationParams,
    ) -> str:
        """Pack auth params into a signed JWT session and redirect to consent page."""
        base_url = os.environ.get("LOCKER_BASE_URL", "https://locker.up.railway.app")
        session_payload = {
            "client_id": client.client_id,
            "state": params.state,
            "code_challenge": params.code_challenge,
            "redirect_uri": str(params.redirect_uri),
            "redirect_uri_provided_explicitly": params.redirect_uri_provided_explicitly,
            "scopes": params.scopes or [],
            "resource": params.resource,
            "exp": int(time.time()) + AUTH_CODE_TTL,
        }
        session_token = pyjwt.encode(session_payload, _jwt_secret(), algorithm="HS256")
        return f"{base_url}/oauth/consent?session={session_token}"

    # --- Authorization codes ---

    async def load_authorization_code(
        self,
        client: OAuthClientInformationFull,
        authorization_code: str,
    ) -> LockerAuthorizationCode | None:
        db = get_db()
        row = await db.fetchrow(
            "SELECT * FROM oauth_codes WHERE code = $1 AND client_id = $2",
            authorization_code,
            client.client_id,
        )
        if row is None:
            return None
        if time.time() > row["expires_at"]:
            await db.execute("DELETE FROM oauth_codes WHERE code = $1", authorization_code)
            return None
        return LockerAuthorizationCode(
            code=row["code"],
            client_id=row["client_id"],
            user_id=row["user_id"],
            team_id=row["team_id"],
            scopes=_parse_scopes(row["scopes"]),
            code_challenge=row["code_challenge"],
            redirect_uri=AnyUrl(row["redirect_uri"]),
            redirect_uri_provided_explicitly=row["redirect_uri_provided_explicitly"],
            resource=row["resource"],
            expires_at=row["expires_at"],
        )

    async def exchange_authorization_code(
        self,
        client: OAuthClientInformationFull,
        authorization_code: LockerAuthorizationCode,
    ) -> OAuthToken:
        db = get_db()
        now = datetime.now(timezone.utc).isoformat()

        # Generate tokens
        access_plain = _generate_opaque_token()
        refresh_plain = _generate_opaque_token()
        access_hash = hash_token(access_plain)
        refresh_hash = hash_token(refresh_plain)

        access_exp = time.time() + ACCESS_TOKEN_TTL
        refresh_exp = time.time() + REFRESH_TOKEN_TTL

        # Store hashed tokens
        await db.execute(
            "INSERT INTO oauth_tokens (token_hash, token_type, client_id, user_id, team_id, scopes, resource, expires_at, created_at) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)",
            access_hash, "access", authorization_code.client_id,
            authorization_code.user_id, authorization_code.team_id,
            " ".join(authorization_code.scopes), authorization_code.resource,
            access_exp, now,
        )
        await db.execute(
            "INSERT INTO oauth_tokens (token_hash, token_type, client_id, user_id, team_id, scopes, resource, expires_at, created_at) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)",
            refresh_hash, "refresh", authorization_code.client_id,
            authorization_code.user_id, authorization_code.team_id,
            " ".join(authorization_code.scopes), authorization_code.resource,
            refresh_exp, now,
        )

        # Delete used code
        await db.execute("DELETE FROM oauth_codes WHERE code = $1", authorization_code.code)

        return OAuthToken(
            access_token=access_plain,
            token_type="Bearer",
            expires_in=ACCESS_TOKEN_TTL,
            scope=" ".join(authorization_code.scopes) if authorization_code.scopes else None,
            refresh_token=refresh_plain,
        )

    # --- Access tokens ---

    async def load_access_token(self, token: str) -> LockerAccessToken | None:
        db = get_db()
        token_hash = hash_token(token)
        row = await db.fetchrow(
            "SELECT * FROM oauth_tokens WHERE token_hash = $1 AND token_type = 'access'",
            token_hash,
        )
        if row is None:
            return None
        if row["revoked"]:
            return None
        if row["expires_at"] and time.time() > row["expires_at"]:
            return None
        return LockerAccessToken(
            token=token,
            client_id=row["client_id"],
            user_id=row["user_id"],
            team_id=row["team_id"],
            scopes=_parse_scopes(row["scopes"]),
            expires_at=int(row["expires_at"]) if row["expires_at"] else None,
            resource=row["resource"],
        )

    # --- Refresh tokens ---

    async def load_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: str,
    ) -> LockerRefreshToken | None:
        db = get_db()
        token_hash = hash_token(refresh_token)
        row = await db.fetchrow(
            "SELECT * FROM oauth_tokens WHERE token_hash = $1 AND token_type = 'refresh' AND client_id = $2",
            token_hash,
            client.client_id,
        )
        if row is None:
            return None
        if row["revoked"]:
            return None
        if row["expires_at"] and time.time() > row["expires_at"]:
            return None
        return LockerRefreshToken(
            token=refresh_token,
            client_id=row["client_id"],
            user_id=row["user_id"],
            team_id=row["team_id"],
            scopes=_parse_scopes(row["scopes"]),
            expires_at=int(row["expires_at"]) if row["expires_at"] else None,
        )

    async def exchange_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: LockerRefreshToken,
        scopes: list[str],
    ) -> OAuthToken:
        db = get_db()
        now = datetime.now(timezone.utc).isoformat()

        # Revoke old tokens for this client+user+team
        old_hash = hash_token(refresh_token.token)
        await db.execute(
            "UPDATE oauth_tokens SET revoked = TRUE WHERE token_hash = $1",
            old_hash,
        )

        # Use requested scopes or fall back to original
        effective_scopes = scopes if scopes else refresh_token.scopes

        # Generate new tokens
        access_plain = _generate_opaque_token()
        new_refresh_plain = _generate_opaque_token()
        access_hash = hash_token(access_plain)
        new_refresh_hash = hash_token(new_refresh_plain)

        access_exp = time.time() + ACCESS_TOKEN_TTL
        refresh_exp = time.time() + REFRESH_TOKEN_TTL

        await db.execute(
            "INSERT INTO oauth_tokens (token_hash, token_type, client_id, user_id, team_id, scopes, resource, expires_at, created_at) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)",
            access_hash, "access", refresh_token.client_id,
            refresh_token.user_id, refresh_token.team_id,
            " ".join(effective_scopes), None,
            access_exp, now,
        )
        await db.execute(
            "INSERT INTO oauth_tokens (token_hash, token_type, client_id, user_id, team_id, scopes, resource, expires_at, created_at) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)",
            new_refresh_hash, "refresh", refresh_token.client_id,
            refresh_token.user_id, refresh_token.team_id,
            " ".join(effective_scopes), None,
            refresh_exp, now,
        )

        return OAuthToken(
            access_token=access_plain,
            token_type="Bearer",
            expires_in=ACCESS_TOKEN_TTL,
            scope=" ".join(effective_scopes) if effective_scopes else None,
            refresh_token=new_refresh_plain,
        )

    # --- Revocation ---

    async def revoke_token(
        self,
        token: LockerAccessToken | LockerRefreshToken,
    ) -> None:
        db = get_db()
        token_hash = hash_token(token.token)
        await db.execute(
            "UPDATE oauth_tokens SET revoked = TRUE WHERE token_hash = $1",
            token_hash,
        )
        # Also revoke all tokens for the same client+user+team (access+refresh pair)
        await db.execute(
            "UPDATE oauth_tokens SET revoked = TRUE "
            "WHERE client_id = $1 AND user_id = $2 AND team_id = $3 AND revoked = FALSE",
            token.client_id,
            token.user_id,
            token.team_id,
        )
