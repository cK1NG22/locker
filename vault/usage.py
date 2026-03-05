"""Usage tracking — logs every skill invocation."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query

from src.auth import require_api_key
from vault.db import get_db

router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_api_key)])


async def log_usage(db, skill_name: str, team_id: Optional[str], source: str) -> None:
    """Insert a usage row. Fire-and-forget; callers should not block on this."""
    await db.execute(
        "INSERT INTO skill_usage (id, skill_name, team_id, invoked_at, source) "
        "VALUES (?, ?, ?, ?, ?)",
        (
            str(uuid.uuid4()),
            skill_name,
            team_id,
            datetime.now(timezone.utc).isoformat(),
            source,
        ),
    )
    await db.commit()


@router.get("/usage")
async def get_usage(skill_name: Optional[str] = Query(None)):
    db = get_db()
    if skill_name:
        cursor = await db.execute(
            "SELECT id, skill_name, team_id, invoked_at, source "
            "FROM skill_usage WHERE skill_name = ? ORDER BY invoked_at DESC",
            (skill_name,),
        )
    else:
        cursor = await db.execute(
            "SELECT id, skill_name, team_id, invoked_at, source "
            "FROM skill_usage ORDER BY invoked_at DESC"
        )
    rows = await cursor.fetchall()
    return {
        "usage": [
            {
                "id": r["id"],
                "skill_name": r["skill_name"],
                "team_id": r["team_id"],
                "invoked_at": r["invoked_at"],
                "source": r["source"],
            }
            for r in rows
        ]
    }


@router.get("/usage/summary")
async def get_usage_summary():
    db = get_db()
    cursor = await db.execute(
        "SELECT skill_name, COUNT(*) as count FROM skill_usage "
        "GROUP BY skill_name ORDER BY count DESC"
    )
    rows = await cursor.fetchall()
    return {
        "summary": [
            {"skill_name": r["skill_name"], "count": r["count"]}
            for r in rows
        ]
    }
