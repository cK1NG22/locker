from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request

from src.middleware.rate_limit import limiter

from vault.crypto import decrypt
from vault.db import get_db
from vault.models import EmployeeSkill
from vault.token_utils import hash_token

router = APIRouter(prefix="/api/v1")


async def _require_team_token(
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


@router.get("/employee/skills")
@limiter.limit("60/minute")
async def get_employee_skills(
    request: Request,
    x_team_token: Optional[str] = Header(None, alias="X-Team-Token"),
):
    team = await _require_team_token(x_team_token)
    db = get_db()
    rows = await db.fetch(
        "SELECT s.id, s.name, s.description, s.visibility, s.content FROM skills s "
        "JOIN team_skills ts ON s.id = ts.skill_id "
        "WHERE ts.team_id = $1 AND s.visibility != 'hidden' AND s.scope = 'team'",
        team["id"],
    )
    skills = []
    for row in rows:
        content = decrypt(row["content"]) if row["visibility"] == "open" else None
        skills.append(EmployeeSkill(id=row["id"], name=row["name"], description=row["description"], content=content))
    return {"team": team["name"], "skills": skills}
