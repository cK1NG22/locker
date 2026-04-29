"""Shared test fixtures — Postgres via testcontainers."""

import asyncio
import base64
import os
from datetime import datetime, timezone

import asyncpg
import jwt as _jwt
import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from testcontainers.postgres import PostgresContainer

# Generate test keys before app is imported
TEST_JWT_SECRET = "test-jwt-secret-that-is-long-enough-for-hs256"
TEST_ENC_KEY = base64.b64encode(AESGCM.generate_key(256)).decode()

os.environ["LOCKER_JWT_SECRET"] = TEST_JWT_SECRET
os.environ["LOCKER_ENCRYPTION_KEY"] = TEST_ENC_KEY
os.environ["GOOGLE_CLIENT_ID"] = "test-client-id.apps.googleusercontent.com"
os.environ["ANTHROPIC_API_KEY"] = "test-anthropic-key"

_TEST_PAYLOAD = {
    "sub": "test-user-id",
    "email": "test@example.com",
    "exp": datetime(2099, 1, 1, tzinfo=timezone.utc),
}
TEST_JWT = _jwt.encode(_TEST_PAYLOAD, TEST_JWT_SECRET, algorithm="HS256")

_OTHER_PAYLOAD = {
    "sub": "other-user-id",
    "email": "other@example.com",
    "exp": datetime(2099, 1, 1, tzinfo=timezone.utc),
}
OTHER_JWT = _jwt.encode(_OTHER_PAYLOAD, TEST_JWT_SECRET, algorithm="HS256")

# Schema DDL for test database
_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id          TEXT PRIMARY KEY,
    email       TEXT NOT NULL UNIQUE,
    name        TEXT,
    google_id   TEXT NOT NULL UNIQUE,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS skills (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    content     TEXT NOT NULL,
    description TEXT,
    visibility  TEXT NOT NULL DEFAULT 'open',
    scope       TEXT NOT NULL DEFAULT 'team',
    uploaded_by TEXT,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS organizations (
    id                TEXT PRIMARY KEY,
    name              TEXT NOT NULL,
    slug              TEXT NOT NULL UNIQUE,
    owner_id          TEXT NOT NULL,
    skill_convention  TEXT NOT NULL DEFAULT '/l',
    created_at        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS org_members (
    id          TEXT PRIMARY KEY,
    org_id      TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id     TEXT NOT NULL,
    role        TEXT NOT NULL DEFAULT 'member',
    UNIQUE(org_id, user_id)
);

CREATE TABLE IF NOT EXISTS teams (
    id               TEXT PRIMARY KEY,
    name             TEXT NOT NULL UNIQUE,
    slug             TEXT UNIQUE,
    token_hash       TEXT NOT NULL UNIQUE,
    token_prefix     TEXT NOT NULL,
    token_encrypted  TEXT,
    invite_code      TEXT UNIQUE,
    owner_id         TEXT,
    org_id           TEXT REFERENCES organizations(id) ON DELETE SET NULL,
    created_at       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS team_members (
    id          TEXT PRIMARY KEY,
    team_id     TEXT NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    user_id     TEXT NOT NULL,
    role        TEXT NOT NULL DEFAULT 'member',
    can_share   BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TEXT NOT NULL,
    UNIQUE(team_id, user_id)
);

CREATE TABLE IF NOT EXISTS team_skills (
    team_id     TEXT NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    skill_id    TEXT NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    PRIMARY KEY (team_id, skill_id)
);

CREATE TABLE IF NOT EXISTS skill_files (
    id          TEXT PRIMARY KEY,
    skill_id    TEXT NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    path        TEXT NOT NULL,
    content     TEXT NOT NULL,
    size_bytes  INTEGER NOT NULL,
    created_at  TEXT NOT NULL,
    UNIQUE(skill_id, path)
);

CREATE TABLE IF NOT EXISTS skill_usage (
    id          TEXT PRIMARY KEY,
    skill_name  TEXT NOT NULL,
    team_id     TEXT,
    invoked_at  TEXT NOT NULL,
    source      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS skill_feedback (
    id          TEXT PRIMARY KEY,
    skill_id    TEXT NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    team_id     TEXT,
    feedback_text TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'pending',
    submitter_team_name TEXT,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS skill_share_requests (
    id              TEXT PRIMARY KEY,
    skill_id        TEXT NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    from_team_id    TEXT NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    to_team_id      TEXT NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    requested_by    TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending',
    created_at      TEXT NOT NULL,
    resolved_at     TEXT,
    resolved_by     TEXT
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id              TEXT PRIMARY KEY,
    actor_id        TEXT NOT NULL,
    action          TEXT NOT NULL,
    resource_type   TEXT NOT NULL,
    resource_id     TEXT,
    metadata        JSONB,
    created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_tokens (
    id          TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL,
    token_hash  TEXT NOT NULL UNIQUE,
    token_prefix TEXT NOT NULL,
    name        TEXT NOT NULL DEFAULT 'default',
    created_at  TEXT NOT NULL,
    revoked_at  TEXT
);

CREATE TABLE IF NOT EXISTS oauth_clients (
    client_id         TEXT PRIMARY KEY,
    client_secret_hash TEXT,
    client_info_json  TEXT NOT NULL,
    created_at        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS oauth_codes (
    code              TEXT PRIMARY KEY,
    client_id         TEXT NOT NULL,
    user_id           TEXT NOT NULL,
    team_id           TEXT NOT NULL,
    scopes            TEXT NOT NULL,
    code_challenge    TEXT NOT NULL,
    redirect_uri      TEXT NOT NULL,
    redirect_uri_provided_explicitly BOOLEAN NOT NULL DEFAULT TRUE,
    resource          TEXT,
    expires_at        DOUBLE PRECISION NOT NULL,
    created_at        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS oauth_tokens (
    token_hash        TEXT PRIMARY KEY,
    token_type        TEXT NOT NULL,
    client_id         TEXT NOT NULL,
    user_id           TEXT NOT NULL,
    team_id           TEXT NOT NULL,
    scopes            TEXT NOT NULL,
    resource          TEXT,
    expires_at        DOUBLE PRECISION,
    created_at        TEXT NOT NULL,
    revoked           BOOLEAN NOT NULL DEFAULT FALSE
);
"""

_TABLES = [
    "oauth_tokens", "oauth_codes", "oauth_clients", "user_tokens",
    "audit_logs", "skill_share_requests", "skill_feedback", "skill_usage",
    "skill_files", "team_skills", "team_members", "teams",
    "org_members", "organizations", "skills", "users",
]


@pytest.fixture(scope="session")
def pg_container():
    """Start a Postgres container once for the entire test session."""
    with PostgresContainer("postgres:16-alpine") as pg:
        # Run schema creation synchronously
        dsn = pg.get_connection_url().replace("psycopg2", "asyncpg").replace("+asyncpg", "")
        # Convert SQLAlchemy-style URL to asyncpg-style
        # testcontainers gives: postgresql+psycopg2://user:pass@host:port/db
        # we need: postgresql://user:pass@host:port/db
        if "+psycopg2" in dsn:
            dsn = dsn.replace("+psycopg2", "")
        if "+asyncpg" in dsn:
            dsn = dsn.replace("+asyncpg", "")

        async def _setup():
            conn = await asyncpg.connect(dsn)
            await conn.execute(_SCHEMA)
            await conn.close()

        asyncio.get_event_loop_policy().new_event_loop().run_until_complete(_setup())
        os.environ["DATABASE_URL"] = dsn
        yield pg


@pytest.fixture(autouse=True)
def _truncate_tables(pg_container):
    """Truncate all tables before each test for isolation."""
    dsn = os.environ["DATABASE_URL"]

    async def _truncate():
        conn = await asyncpg.connect(dsn)
        # Disable FK checks during truncate
        await conn.execute(
            f"TRUNCATE {', '.join(_TABLES)} CASCADE"
        )
        await conn.close()

    loop = asyncio.get_event_loop_policy().new_event_loop()
    loop.run_until_complete(_truncate())
    loop.close()

    # Reset rate limiter state so limits don't leak between tests
    from src.middleware.rate_limit import limiter
    limiter.reset()
