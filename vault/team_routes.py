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
    TeamSkillsSet,
)

router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_user)])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.post("/teams", status_code=201, response_model=TeamOut)
async def create_team(body: TeamCreate):
    team_id = str(uuid.uuid4())
    token = str(uuid.uuid4())
    now = _now()
    db = get_db()
    try:
        await db.execute(
            "INSERT INTO teams (id, name, token, created_at) VALUES (?, ?, ?, ?)",
            (team_id, body.name, token, now),
        )
        await db.commit()
    except Exception as e:
        if "UNIQUE constraint failed" in str(e):
            raise HTTPException(status_code=409, detail=f"Team '{body.name}' already exists")
        raise
    return TeamOut(id=team_id, name=body.name, token=token, created_at=now)


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
        "SELECT id, name, token, created_at FROM teams WHERE id = ?", (team_id,)
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
    return TeamDetail(
        id=row["id"],
        name=row["name"],
        token=row["token"],
        created_at=row["created_at"],
        skills=skill_names,
    )


@router.put("/teams/{team_id}", response_model=TeamOut)
async def update_team(team_id: str, body: TeamUpdate):
    db = get_db()
    cursor = await db.execute(
        "SELECT id, name, token, created_at FROM teams WHERE id = ?", (team_id,)
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
        id=row["id"], name=body.name, token=row["token"], created_at=row["created_at"]
    )


@router.delete("/teams/{team_id}", status_code=204)
async def delete_team(team_id: str):
    db = get_db()
    cursor = await db.execute("SELECT id FROM teams WHERE id = ?", (team_id,))
    row = await cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Team not found")
    await db.execute("DELETE FROM teams WHERE id = ?", (team_id,))
    await db.commit()


@router.put("/teams/{team_id}/skills", status_code=200)
async def set_team_skills(team_id: str, body: TeamSkillsSet):
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
