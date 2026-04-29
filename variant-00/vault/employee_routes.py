from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request

from src.middleware.rate_limit import limiter

from vault.crypto import decrypt
from vault.db import get_db
from vault.helpers import require_team_token, resolve_user_from_pat
from vault.models import EmployeeSkill

router = APIRouter(prefix="/api/v1")


async def _get_team_skills(team_id: str):
    db = get_db()
    rows = await db.fetch(
        "SELECT s.id, s.name, s.description, s.visibility, s.content FROM skills s "
        "JOIN team_skills ts ON s.id = ts.skill_id "
        "WHERE ts.team_id = $1 AND s.visibility != 'hidden' AND s.scope = 'team'",
        team_id,
    )
    skills = []
    for row in rows:
        content = None
        if row["visibility"] == "open":
            try:
                content = decrypt(row["content"])
            except Exception:
                content = "[Error: skill content could not be decrypted — contact admin]"
        skills.append(EmployeeSkill(id=row["id"], name=row["name"], description=row["description"], content=content))
    return skills


async def _get_convention(team_id: str) -> str:
    db = get_db()
    convention = "/l"
    team_row = await db.fetchrow("SELECT org_id FROM teams WHERE id = $1", team_id)
    if team_row and team_row["org_id"]:
        org_row = await db.fetchrow(
            "SELECT skill_convention FROM organizations WHERE id = $1",
            team_row["org_id"],
        )
        if org_row:
            convention = org_row["skill_convention"]
    return convention


async def _resolve_teams(
    x_user_token: Optional[str], x_team_token: Optional[str],
) -> list[dict]:
    """Resolve auth header to a list of {id, name} team dicts."""
    if x_user_token:
        user_info = await resolve_user_from_pat(x_user_token)
        if user_info is None:
            raise HTTPException(status_code=401, detail="Unauthorized")
        return user_info["teams"]
    team = await require_team_token(x_team_token)
    return [team]


@router.get("/employee/skills")
@limiter.limit("60/minute")
async def get_employee_skills(
    request: Request,
    x_team_token: Optional[str] = Header(None, alias="X-Team-Token"),
    x_user_token: Optional[str] = Header(None, alias="X-User-Token"),
):
    teams = await _resolve_teams(x_user_token, x_team_token)
    all_skills: list = []
    seen_ids: set = set()
    convention = "/l"
    team_name = ""
    for t in teams:
        for s in await _get_team_skills(t["id"]):
            if s.id not in seen_ids:
                all_skills.append(s)
                seen_ids.add(s.id)
        if not team_name:
            team_name = t["name"]
            convention = await _get_convention(t["id"])
    return {"team": team_name, "convention": convention, "skills": all_skills}
