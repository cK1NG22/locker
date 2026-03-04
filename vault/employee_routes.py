from typing import Optional

from fastapi import APIRouter, Header, HTTPException

from vault.crypto import decrypt
from vault.db import get_db
from vault.models import EmployeeSkill

router = APIRouter(prefix="/api/v1")


async def _require_team_token(
    x_team_token: Optional[str] = Header(None, alias="X-Team-Token"),
) -> dict:
    if not x_team_token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    db = get_db()
    cursor = await db.execute(
        "SELECT id, name FROM teams WHERE token = ?", (x_team_token,)
    )
    row = await cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return {"id": row["id"], "name": row["name"]}


@router.get("/employee/skills")
async def get_employee_skills(
    x_team_token: Optional[str] = Header(None, alias="X-Team-Token"),
):
    team = await _require_team_token(x_team_token)
    db = get_db()
    cursor = await db.execute(
        "SELECT s.name, s.description, s.visibility, s.content FROM skills s "
        "JOIN team_skills ts ON s.id = ts.skill_id "
        "WHERE ts.team_id = ? AND s.visibility != 'hidden'",
        (team["id"],),
    )
    rows = await cursor.fetchall()
    skills = []
    for row in rows:
        content = decrypt(row["content"]) if row["visibility"] == "open" else None
        skills.append(EmployeeSkill(name=row["name"], description=row["description"], content=content))
    return {"team": team["name"], "skills": skills}
