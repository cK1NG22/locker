from datetime import datetime, timezone
from typing import Optional

from fastapi import Header, HTTPException

from vault.db import get_db
from vault.token_utils import hash_token


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def require_team_token(
    x_team_token: Optional[str] = Header(None, alias="X-Team-Token"),
) -> dict:
    if not x_team_token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    db = get_db()
    hashed = hash_token(x_team_token)
    row = await db.fetchrow(
        "SELECT id, name FROM teams WHERE token_hash = $1", hashed
    )
    if row is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return {"id": row["id"], "name": row["name"]}


async def require_team_admin(team_id: str, user_id: str) -> None:
    """Raise 403 if user is not an admin member of the team.
    NULL-owner teams (pre-3.2) are editable by any authenticated user.
    """
    db = get_db()
    row = await db.fetchrow("SELECT owner_id FROM teams WHERE id = $1", team_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Team not found")
    # Legacy teams with no owner: allow any authenticated user
    if row["owner_id"] is None:
        return
    member = await db.fetchrow(
        "SELECT role FROM team_members WHERE team_id = $1 AND user_id = $2",
        team_id, user_id,
    )
    if member is None or member["role"] != "admin":
        raise HTTPException(status_code=403, detail="Team admin access required")
