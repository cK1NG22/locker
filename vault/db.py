import os
import aiosqlite
from typing import Optional

CREATE_SKILLS = """
CREATE TABLE IF NOT EXISTS skills (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    content     TEXT NOT NULL,
    description TEXT,
    visibility  TEXT NOT NULL DEFAULT 'open',
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
)
"""

CREATE_TEAMS = """
CREATE TABLE IF NOT EXISTS teams (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    token       TEXT NOT NULL UNIQUE,
    created_at  TEXT NOT NULL
)
"""

CREATE_TEAM_SKILLS = """
CREATE TABLE IF NOT EXISTS team_skills (
    team_id     TEXT NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    skill_id    TEXT NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    PRIMARY KEY (team_id, skill_id)
)
"""

CREATE_SKILL_FILES = """
CREATE TABLE IF NOT EXISTS skill_files (
    id          TEXT PRIMARY KEY,
    skill_id    TEXT NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    path        TEXT NOT NULL,
    content     TEXT NOT NULL,
    size_bytes  INTEGER NOT NULL,
    created_at  TEXT NOT NULL,
    UNIQUE(skill_id, path)
)
"""

CREATE_SKILL_USAGE = """
CREATE TABLE IF NOT EXISTS skill_usage (
    id          TEXT PRIMARY KEY,
    skill_name  TEXT NOT NULL,
    team_id     TEXT,
    invoked_at  TEXT NOT NULL,
    source      TEXT NOT NULL
)
"""

CREATE_SKILL_FEEDBACK = """
CREATE TABLE IF NOT EXISTS skill_feedback (
    id          TEXT PRIMARY KEY,
    skill_id    TEXT NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    team_id     TEXT,
    feedback_text TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'pending',
    created_at  TEXT NOT NULL
)
"""

_db: Optional[aiosqlite.Connection] = None


async def init_db() -> None:
    global _db
    path = os.environ.get("LOCKER_DB_PATH", "./locker.db")
    _db = await aiosqlite.connect(path)
    _db.row_factory = aiosqlite.Row
    await _db.execute("PRAGMA foreign_keys = ON")
    await _db.execute(CREATE_SKILLS)
    await _db.execute(CREATE_TEAMS)
    await _db.execute(CREATE_TEAM_SKILLS)
    await _db.execute(CREATE_SKILL_FILES)
    await _db.execute(CREATE_SKILL_USAGE)
    await _db.execute(CREATE_SKILL_FEEDBACK)
    # Migrate existing DBs that lack the visibility column
    try:
        await _db.execute(
            "ALTER TABLE skills ADD COLUMN visibility TEXT NOT NULL DEFAULT 'hidden'"
        )
    except Exception:
        pass  # Column already exists
    await _db.commit()


async def close_db() -> None:
    global _db
    if _db is not None:
        await _db.close()
        _db = None


def get_db() -> aiosqlite.Connection:
    if _db is None:
        raise RuntimeError("Database not initialized. Did app lifespan run?")
    return _db
