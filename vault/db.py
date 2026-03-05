import os
import aiosqlite
from typing import Optional

CREATE_SKILLS = """
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
)
"""

CREATE_TEAMS = """
CREATE TABLE IF NOT EXISTS teams (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    token       TEXT NOT NULL UNIQUE,
    owner_id    TEXT,
    created_at  TEXT NOT NULL
)
"""

CREATE_TEAM_MEMBERS = """
CREATE TABLE IF NOT EXISTS team_members (
    id          TEXT PRIMARY KEY,
    team_id     TEXT NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    user_id     TEXT NOT NULL,
    role        TEXT NOT NULL DEFAULT 'member',
    can_share   INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL,
    UNIQUE(team_id, user_id)
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

CREATE_USERS = """
CREATE TABLE IF NOT EXISTS users (
    id          TEXT PRIMARY KEY,
    email       TEXT NOT NULL UNIQUE,
    name        TEXT,
    google_id   TEXT NOT NULL UNIQUE,
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
    await _db.execute(CREATE_TEAM_MEMBERS)
    await _db.execute(CREATE_TEAM_SKILLS)
    await _db.execute(CREATE_SKILL_FILES)
    await _db.execute(CREATE_SKILL_USAGE)
    await _db.execute(CREATE_SKILL_FEEDBACK)
    await _db.execute(CREATE_USERS)
    # Migrate existing DBs that lack newer columns
    for migration in [
        "ALTER TABLE skills ADD COLUMN visibility TEXT NOT NULL DEFAULT 'hidden'",
        "ALTER TABLE skills ADD COLUMN scope TEXT NOT NULL DEFAULT 'team'",
        "ALTER TABLE skills ADD COLUMN uploaded_by TEXT",
        "ALTER TABLE teams ADD COLUMN owner_id TEXT",
    ]:
        try:
            await _db.execute(migration)
        except Exception:
            pass  # Column already exists
    # Migration: remove UNIQUE constraint on skills.name (task 3.5)
    # SQLite requires a table rebuild to drop a UNIQUE constraint
    try:
        idx_cursor = await _db.execute("PRAGMA index_list(skills)")
        indexes = await idx_cursor.fetchall()
        has_name_unique = False
        for idx in indexes:
            if idx["unique"] == 1:
                info_cursor = await _db.execute(f"PRAGMA index_info('{idx['name']}')")
                cols = await info_cursor.fetchall()
                if any(col["name"] == "name" for col in cols):
                    has_name_unique = True
                    break
        if has_name_unique:
            await _db.execute("PRAGMA foreign_keys = OFF")
            await _db.execute(
                """CREATE TABLE IF NOT EXISTS skills_new (
                    id          TEXT PRIMARY KEY,
                    name        TEXT NOT NULL,
                    content     TEXT NOT NULL,
                    description TEXT,
                    visibility  TEXT NOT NULL DEFAULT 'open',
                    scope       TEXT NOT NULL DEFAULT 'team',
                    uploaded_by TEXT,
                    created_at  TEXT NOT NULL,
                    updated_at  TEXT NOT NULL
                )"""
            )
            await _db.execute("INSERT INTO skills_new SELECT * FROM skills")
            await _db.execute("DROP TABLE skills")
            await _db.execute("ALTER TABLE skills_new RENAME TO skills")
            await _db.execute("PRAGMA foreign_keys = ON")
    except Exception:
        pass  # Already migrated or error
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
