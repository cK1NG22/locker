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
        id          TEXT PRIMARY KEY,
        name        TEXT NOT NULL UNIQUE,
        token       TEXT NOT NULL UNIQUE,
        owner_id    TEXT,
        org_id      TEXT REFERENCES organizations(id) ON DELETE SET NULL,
        created_at  TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS team_members (
        id          TEXT PRIMARY KEY,
        team_id     TEXT NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
        user_id     TEXT NOT NULL,
        role        TEXT NOT NULL DEFAULT 'member',
        can_share   INTEGER NOT NULL DEFAULT 0,
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
]


async def init_db() -> None:
    global _pool
    dsn = os.environ.get("DATABASE_URL", "postgresql://localhost/locker")
    _pool = await asyncpg.create_pool(dsn, min_size=2, max_size=10)
    async with _pool.acquire() as conn:
        for stmt in _CREATE_TABLES:
            await conn.execute(stmt)


async def close_db() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_db() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("Database not initialized. Did app lifespan run?")
    return _pool
