import os
import asyncpg
from typing import Optional

_pool: Optional[asyncpg.Pool] = None

_CREATE_TABLES = [
    """CREATE TABLE IF NOT EXISTS users (
        id          TEXT PRIMARY KEY,
        email       TEXT NOT NULL UNIQUE,
        name        TEXT,
        google_id   TEXT NOT NULL UNIQUE,
        created_at  TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS skills (
        id          TEXT PRIMARY KEY,
        name        TEXT NOT NULL,
        content     TEXT NOT NULL,
        description TEXT,
        visibility  TEXT NOT NULL DEFAULT 'open',
        scope       TEXT NOT NULL DEFAULT 'team',
        uploaded_by TEXT,
        created_at  TEXT NOT NULL,
        updated_at  TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS organizations (
        id                TEXT PRIMARY KEY,
        name              TEXT NOT NULL,
        slug              TEXT NOT NULL UNIQUE,
        owner_id          TEXT NOT NULL,
        skill_convention  TEXT NOT NULL DEFAULT '/l',
        created_at        TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS org_members (
        id          TEXT PRIMARY KEY,
        org_id      TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
        user_id     TEXT NOT NULL,
        role        TEXT NOT NULL DEFAULT 'member',
        UNIQUE(org_id, user_id)
    )""",
    """CREATE TABLE IF NOT EXISTS teams (
        id           TEXT PRIMARY KEY,
        name         TEXT NOT NULL UNIQUE,
        slug         TEXT UNIQUE,
        token_hash   TEXT NOT NULL UNIQUE,
        token_prefix TEXT NOT NULL,
        token_encrypted TEXT,
        invite_code  TEXT UNIQUE,
        owner_id     TEXT,
        org_id       TEXT REFERENCES organizations(id) ON DELETE SET NULL,
        created_at   TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS team_members (
        id          TEXT PRIMARY KEY,
        team_id     TEXT NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
        user_id     TEXT NOT NULL,
        role        TEXT NOT NULL DEFAULT 'member',
        can_share   BOOLEAN NOT NULL DEFAULT FALSE,
        created_at  TEXT NOT NULL,
        UNIQUE(team_id, user_id)
    )""",
    """CREATE TABLE IF NOT EXISTS team_skills (
        team_id     TEXT NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
        skill_id    TEXT NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
        PRIMARY KEY (team_id, skill_id)
    )""",
    """CREATE TABLE IF NOT EXISTS skill_files (
        id          TEXT PRIMARY KEY,
        skill_id    TEXT NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
        path        TEXT NOT NULL,
        content     TEXT NOT NULL,
        size_bytes  INTEGER NOT NULL,
        created_at  TEXT NOT NULL,
        UNIQUE(skill_id, path)
    )""",
    """CREATE TABLE IF NOT EXISTS skill_share_requests (
        id              TEXT PRIMARY KEY,
        skill_id        TEXT NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
        from_team_id    TEXT NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
        to_team_id      TEXT NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
        requested_by    TEXT NOT NULL,
        status          TEXT NOT NULL DEFAULT 'pending',
        created_at      TEXT NOT NULL,
        resolved_at     TEXT,
        resolved_by     TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS skill_usage (
        id          TEXT PRIMARY KEY,
        skill_name  TEXT NOT NULL,
        team_id     TEXT,
        invoked_at  TEXT NOT NULL,
        source      TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS skill_feedback (
        id          TEXT PRIMARY KEY,
        skill_id    TEXT NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
        team_id     TEXT,
        feedback_text TEXT NOT NULL,
        status      TEXT NOT NULL DEFAULT 'pending',
        submitter_team_name TEXT,
        created_at  TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS audit_logs (
        id              TEXT PRIMARY KEY,
        actor_id        TEXT NOT NULL,
        action          TEXT NOT NULL,
        resource_type   TEXT NOT NULL,
        resource_id     TEXT,
        metadata        JSONB,
        created_at      TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS user_tokens (
        id          TEXT PRIMARY KEY,
        user_id     TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        token_hash  TEXT NOT NULL UNIQUE,
        token_prefix TEXT NOT NULL,
        name        TEXT NOT NULL DEFAULT 'default',
        created_at  TEXT NOT NULL,
        revoked_at  TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS oauth_clients (
        client_id         TEXT PRIMARY KEY,
        client_secret_hash TEXT,
        client_info_json  TEXT NOT NULL,
        created_at        TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS oauth_codes (
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
    )""",
    """CREATE TABLE IF NOT EXISTS oauth_tokens (
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
    )""",
]


async def init_db() -> None:
    global _pool
    dsn = os.environ.get("DATABASE_URL", "postgresql://localhost/locker")

    _pool = await asyncpg.create_pool(dsn, min_size=2, max_size=10)
    async with _pool.acquire() as conn:
        for stmt in _CREATE_TABLES:
            await conn.execute(stmt)
        # One-time migrations for existing tables
        await conn.execute("ALTER TABLE teams ADD COLUMN IF NOT EXISTS slug TEXT UNIQUE")
        await conn.execute("ALTER TABLE teams ADD COLUMN IF NOT EXISTS token_encrypted TEXT")
        await conn.execute("ALTER TABLE teams ADD COLUMN IF NOT EXISTS invite_code TEXT UNIQUE")
        # Backfill slugs for teams that don't have one
        import re
        rows = await conn.fetch("SELECT id, name FROM teams WHERE slug IS NULL")
        for row in rows:
            slug = re.sub(r'-+', '-', re.sub(r'[\s]+', '-', re.sub(r'[^a-z0-9\s-]', '', row["name"].lower().strip()))).strip('-')
            counter = 0
            while True:
                candidate = slug if counter == 0 else f"{slug}-{counter}"
                existing = await conn.fetchval("SELECT 1 FROM teams WHERE slug = $1", candidate)
                if not existing:
                    await conn.execute("UPDATE teams SET slug = $1 WHERE id = $2", candidate, row["id"])
                    break
                counter += 1
        # Backfill invite codes for teams that don't have one
        from vault.token_utils import generate_invite_code
        rows = await conn.fetch("SELECT id, name FROM teams WHERE invite_code IS NULL")
        for row in rows:
            code = generate_invite_code(row["name"])
            while await conn.fetchval("SELECT 1 FROM teams WHERE invite_code = $1", code):
                code = generate_invite_code(row["name"])
            await conn.execute("UPDATE teams SET invite_code = $1 WHERE id = $2", code, row["id"])


async def close_db() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_db() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("Database not initialized. Did app lifespan run?")
    return _pool
