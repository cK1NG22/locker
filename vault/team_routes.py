import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from src.auth import require_user
from vault.db import get_db
from vault.models import (
    TeamCreate,
    TeamUpdate,
    TeamOut,
    TeamSummary,
    TeamDetail,
    TeamMemberOut,
    TeamSkillsSet,
)

router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_user)])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _require_team_admin(team_id: str, user_id: str) -> None:
    """Raise 403 if user is not an admin member of the team.
    NULL-owner teams (pre-3.2) are editable by any authenticated user.
    """
    db = get_db()
    cursor = await db.execute("SELECT owner_id FROM teams WHERE id = ?", (team_id,))
    row = await cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Team not found")
    # Legacy teams with no owner: allow any authenticated user
    if row["owner_id"] is None:
        return
    member_cursor = await db.execute(
        "SELECT role FROM team_members WHERE team_id = ? AND user_id = ?",
        (team_id, user_id),
    )
    member = await member_cursor.fetchone()
    if member is None or member["role"] != "admin":
        raise HTTPException(status_code=403, detail="Team admin access required")


@router.post("/teams", status_code=201, response_model=TeamOut)
async def create_team(body: TeamCreate, user: dict = Depends(require_user)):
    team_id = str(uuid.uuid4())
    member_id = str(uuid.uuid4())
    token = str(uuid.uuid4())
    now = _now()
    user_id = user["sub"]
    db = get_db()
    try:
        await db.execute(
            "INSERT INTO teams (id, name, token, owner_id, created_at) VALUES (?, ?, ?, ?, ?)",
            (team_id, body.name, token, user_id, now),
        )
    except Exception as e:
        if "UNIQUE constraint failed" in str(e):
            raise HTTPException(status_code=409, detail=f"Team '{body.name}' already exists")
        raise
    await db.execute(
        "INSERT INTO team_members (id, team_id, user_id, role, can_share, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (member_id, team_id, user_id, "admin", 1, now),
    )
    await db.commit()
    return TeamOut(id=team_id, name=body.name, token=token, owner_id=user_id, created_at=now)


@router.get("/teams", response_model=list[TeamSummary])
async def list_teams():
    db = get_db()
    cursor = await db.execute(
        "SELECT t.id, t.name, COUNT(ts.skill_id) AS skill_count "
        "FROM teams t LEFT JOIN team_skills ts ON t.id = ts.team_id "
        "GROUP BY t.id, t.name"
    )
    rows = await cursor.fetchall()
    return [
        TeamSummary(id=row["id"], name=row["name"], skill_count=row["skill_count"])
        for row in rows
    ]


@router.get("/teams/{team_id}", response_model=TeamDetail)
async def get_team(team_id: str):
    db = get_db()
    cursor = await db.execute(
        "SELECT id, name, token, owner_id, created_at FROM teams WHERE id = ?", (team_id,)
    )
    row = await cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Team not found")
    skill_cursor = await db.execute(
        "SELECT s.name FROM skills s JOIN team_skills ts ON s.id = ts.skill_id WHERE ts.team_id = ?",
        (team_id,),
    )
    skill_rows = await skill_cursor.fetchall()
    skill_names = [r["name"] for r in skill_rows]
    member_cursor = await db.execute(
        "SELECT id, user_id, role, can_share, created_at FROM team_members WHERE team_id = ?",
        (team_id,),
    )
    member_rows = await member_cursor.fetchall()
    members = [
        TeamMemberOut(
            id=r["id"],
            user_id=r["user_id"],
            role=r["role"],
            can_share=bool(r["can_share"]),
            created_at=r["created_at"],
        )
        for r in member_rows
    ]
    return TeamDetail(
        id=row["id"],
        name=row["name"],
        token=row["token"],
        owner_id=row["owner_id"],
        created_at=row["created_at"],
        skills=skill_names,
        members=members,
    )


@router.put("/teams/{team_id}", response_model=TeamOut)
async def update_team(team_id: str, body: TeamUpdate, user: dict = Depends(require_user)):
    await _require_team_admin(team_id, user["sub"])
    db = get_db()
    cursor = await db.execute(
        "SELECT id, name, token, owner_id, created_at FROM teams WHERE id = ?", (team_id,)
    )
    row = await cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Team not found")
    try:
        await db.execute(
            "UPDATE teams SET name = ? WHERE id = ?", (body.name, team_id)
        )
        await db.commit()
    except Exception as e:
        if "UNIQUE constraint failed" in str(e):
            raise HTTPException(status_code=409, detail=f"Team '{body.name}' already exists")
        raise
    return TeamOut(
        id=row["id"], name=body.name, token=row["token"], owner_id=row["owner_id"], created_at=row["created_at"]
    )


@router.delete("/teams/{team_id}", status_code=204)
async def delete_team(team_id: str, user: dict = Depends(require_user)):
    await _require_team_admin(team_id, user["sub"])
    db = get_db()
    await db.execute("DELETE FROM teams WHERE id = ?", (team_id,))
    await db.commit()


@router.put("/teams/{team_id}/skills", status_code=200)
async def set_team_skills(team_id: str, body: TeamSkillsSet, user: dict = Depends(require_user)):
    await _require_team_admin(team_id, user["sub"])
    db = get_db()
    cursor = await db.execute("SELECT id FROM teams WHERE id = ?", (team_id,))
    if await cursor.fetchone() is None:
        raise HTTPException(status_code=404, detail="Team not found")
    # Validate all skill IDs exist
    for sid in body.skill_ids:
        c = await db.execute("SELECT id FROM skills WHERE id = ?", (sid,))
        if await c.fetchone() is None:
            raise HTTPException(status_code=404, detail=f"Skill '{sid}' not found")
    # Replace all assignments
    await db.execute("DELETE FROM team_skills WHERE team_id = ?", (team_id,))
    for sid in body.skill_ids:
        await db.execute(
            "INSERT INTO team_skills (team_id, skill_id) VALUES (?, ?)",
            (team_id, sid),
        )
    await db.commit()
    return {"ok": True}
