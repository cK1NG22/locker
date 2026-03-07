import re
import uuid

from asyncpg import UniqueViolationError
from fastapi import APIRouter, Depends, HTTPException

from src.auth import require_user
from vault.audit import audit
from vault.db import get_db
from vault.helpers import utc_now, require_team_admin
from vault.models import (
    OrgCreate,
    OrgUpdate,
    OrgOut,
    OrgDetail,
    OrgMemberOut,
    OrgMemberAdd,
    TeamSummary,
)

router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_user)])

SLUG_RE = re.compile(r"^[a-z0-9-]{2,32}$")


async def _require_org_member(org_id: str, user_id: str) -> None:
    db = get_db()
    row = await db.fetchrow(
        "SELECT id FROM org_members WHERE org_id = $1 AND user_id = $2",
        org_id, user_id,
    )
    if row is None:
        raise HTTPException(status_code=403, detail="Org membership required")


async def _require_org_admin(org_id: str, user_id: str) -> None:
    db = get_db()
    row = await db.fetchrow(
        "SELECT role FROM org_members WHERE org_id = $1 AND user_id = $2",
        org_id, user_id,
    )
    if row is None or row["role"] != "org_admin":
        raise HTTPException(status_code=403, detail="Org admin access required")


@router.post("/orgs", status_code=201, response_model=OrgOut)
async def create_org(body: OrgCreate, user: dict = Depends(require_user)):
    if not SLUG_RE.match(body.slug):
        raise HTTPException(status_code=422, detail="Slug must be 2-32 lowercase alphanumeric or hyphens")
    org_id = str(uuid.uuid4())
    member_id = str(uuid.uuid4())
    now = utc_now()
    user_id = user["sub"]
    db = get_db()
    async with db.acquire() as conn:
        async with conn.transaction():
            try:
                await conn.execute(
                    "INSERT INTO organizations (id, name, slug, owner_id, created_at) VALUES ($1, $2, $3, $4, $5)",
                    org_id, body.name, body.slug, user_id, now,
                )
            except UniqueViolationError:
                raise HTTPException(status_code=409, detail=f"Slug '{body.slug}' already taken")
            await conn.execute(
                "INSERT INTO org_members (id, org_id, user_id, role) VALUES ($1, $2, $3, $4)",
                member_id, org_id, user_id, "org_admin",
            )
    await audit(db, user_id, "org.create", "org", org_id, {"name": body.name, "slug": body.slug})
    return OrgOut(id=org_id, name=body.name, slug=body.slug, owner_id=user_id, skill_convention="/l", created_at=now)


@router.get("/orgs", response_model=list[OrgOut])
async def list_orgs(user: dict = Depends(require_user)):
    db = get_db()
    rows = await db.fetch(
        "SELECT o.id, o.name, o.slug, o.owner_id, o.skill_convention, o.created_at "
        "FROM organizations o JOIN org_members om ON o.id = om.org_id "
        "WHERE om.user_id = $1",
        user["sub"],
    )
    return [
        OrgOut(id=r["id"], name=r["name"], slug=r["slug"], owner_id=r["owner_id"],
               skill_convention=r["skill_convention"], created_at=r["created_at"])
        for r in rows
    ]


@router.get("/orgs/{org_id}", response_model=OrgDetail)
async def get_org(org_id: str, user: dict = Depends(require_user)):
    await _require_org_member(org_id, user["sub"])
    db = get_db()
    row = await db.fetchrow(
        "SELECT id, name, slug, owner_id, skill_convention, created_at FROM organizations WHERE id = $1",
        org_id,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Org not found")
    # Teams linked to this org
    team_rows = await db.fetch(
        "SELECT t.id, t.name, COUNT(ts.skill_id) AS skill_count "
        "FROM teams t LEFT JOIN team_skills ts ON t.id = ts.team_id "
        "WHERE t.org_id = $1 GROUP BY t.id, t.name",
        org_id,
    )
    teams = [TeamSummary(id=r["id"], name=r["name"], skill_count=r["skill_count"]) for r in team_rows]
    # Members
    member_rows = await db.fetch(
        "SELECT om.id, om.user_id, u.email, u.name, om.role "
        "FROM org_members om LEFT JOIN users u ON om.user_id = u.id "
        "WHERE om.org_id = $1",
        org_id,
    )
    members = [
        OrgMemberOut(id=r["id"], user_id=r["user_id"], email=r["email"], name=r["name"], role=r["role"])
        for r in member_rows
    ]
    return OrgDetail(
        id=row["id"], name=row["name"], slug=row["slug"], owner_id=row["owner_id"],
        skill_convention=row["skill_convention"], created_at=row["created_at"],
        teams=teams, members=members,
    )


@router.put("/orgs/{org_id}", response_model=OrgOut)
async def update_org(org_id: str, body: OrgUpdate, user: dict = Depends(require_user)):
    await _require_org_admin(org_id, user["sub"])
    db = get_db()
    row = await db.fetchrow("SELECT * FROM organizations WHERE id = $1", org_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Org not found")
    new_name = body.name if body.name is not None else row["name"]
    new_slug = body.slug if body.slug is not None else row["slug"]
    new_convention = body.skill_convention if body.skill_convention is not None else row["skill_convention"]
    if body.slug is not None and not SLUG_RE.match(body.slug):
        raise HTTPException(status_code=422, detail="Slug must be 2-32 lowercase alphanumeric or hyphens")
    try:
        await db.execute(
            "UPDATE organizations SET name = $1, slug = $2, skill_convention = $3 WHERE id = $4",
            new_name, new_slug, new_convention, org_id,
        )
    except UniqueViolationError:
        raise HTTPException(status_code=409, detail=f"Slug '{new_slug}' already taken")
    await audit(db, user["sub"], "org.update", "org", org_id, {"name": new_name, "slug": new_slug})
    return OrgOut(id=org_id, name=new_name, slug=new_slug, owner_id=row["owner_id"],
                  skill_convention=new_convention, created_at=row["created_at"])


@router.delete("/orgs/{org_id}", status_code=204)
async def delete_org(org_id: str, user: dict = Depends(require_user)):
    db = get_db()
    row = await db.fetchrow("SELECT owner_id FROM organizations WHERE id = $1", org_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Org not found")
    if row["owner_id"] != user["sub"]:
        raise HTTPException(status_code=403, detail="Only the org owner can delete it")
    await db.execute("DELETE FROM organizations WHERE id = $1", org_id)
    await audit(db, user["sub"], "org.delete", "org", org_id)


# --- Member management ---


@router.post("/orgs/{org_id}/members", status_code=201, response_model=OrgMemberOut)
async def add_org_member(org_id: str, body: OrgMemberAdd, user: dict = Depends(require_user)):
    await _require_org_admin(org_id, user["sub"])
    db = get_db()
    # Verify org exists
    org = await db.fetchrow("SELECT id FROM organizations WHERE id = $1", org_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Org not found")
    # Look up user by email
    user_row = await db.fetchrow("SELECT id, email, name FROM users WHERE email = $1", body.email)
    if user_row is None:
        raise HTTPException(status_code=404, detail=f"User '{body.email}' not found")
    member_id = str(uuid.uuid4())
    try:
        await db.execute(
            "INSERT INTO org_members (id, org_id, user_id, role) VALUES ($1, $2, $3, $4)",
            member_id, org_id, user_row["id"], "member",
        )
    except UniqueViolationError:
        raise HTTPException(status_code=409, detail="User is already a member of this org")
    await audit(db, user["sub"], "org.member.add", "org_member", member_id, {"org_id": org_id, "email": body.email})
    return OrgMemberOut(id=member_id, user_id=user_row["id"], email=user_row["email"], name=user_row["name"], role="member")


@router.patch("/orgs/{org_id}/members/{member_id}", response_model=OrgMemberOut)
async def update_org_member(org_id: str, member_id: str, body: dict, user: dict = Depends(require_user)):
    await _require_org_admin(org_id, user["sub"])
    db = get_db()
    row = await db.fetchrow(
        "SELECT om.id, om.user_id, u.email, u.name, om.role "
        "FROM org_members om LEFT JOIN users u ON om.user_id = u.id "
        "WHERE om.id = $1 AND om.org_id = $2",
        member_id, org_id,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Member not found")
    new_role = body.get("role", row["role"])
    if new_role not in ("org_admin", "member"):
        raise HTTPException(status_code=422, detail="Role must be 'org_admin' or 'member'")
    await db.execute("UPDATE org_members SET role = $1 WHERE id = $2", new_role, member_id)
    await audit(db, user["sub"], "org.member.update", "org_member", member_id, {"org_id": org_id, "role": new_role})
    return OrgMemberOut(id=row["id"], user_id=row["user_id"], email=row["email"], name=row["name"], role=new_role)


@router.delete("/orgs/{org_id}/members/{member_id}", status_code=204)
async def remove_org_member(org_id: str, member_id: str, user: dict = Depends(require_user)):
    await _require_org_admin(org_id, user["sub"])
    db = get_db()
    row = await db.fetchrow(
        "SELECT user_id FROM org_members WHERE id = $1 AND org_id = $2",
        member_id, org_id,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Member not found")
    # Prevent removing org owner
    org = await db.fetchrow("SELECT owner_id FROM organizations WHERE id = $1", org_id)
    if org and row["user_id"] == org["owner_id"]:
        raise HTTPException(status_code=400, detail="Cannot remove the org owner")
    await db.execute("DELETE FROM org_members WHERE id = $1 AND org_id = $2", member_id, org_id)
    await audit(db, user["sub"], "org.member.remove", "org_member", member_id, {"org_id": org_id})


# --- Team linking ---


@router.post("/orgs/{org_id}/teams/{team_id}", status_code=200)
async def link_team_to_org(org_id: str, team_id: str, user: dict = Depends(require_user)):
    await _require_org_admin(org_id, user["sub"])
    db = get_db()
    # Verify org exists
    org = await db.fetchrow("SELECT id FROM organizations WHERE id = $1", org_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Org not found")
    # Verify team exists and user is team admin
    team = await db.fetchrow("SELECT id, org_id FROM teams WHERE id = $1", team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found")
    # Check team admin permission
    await require_team_admin(team_id, user["sub"])
    if team["org_id"] is not None and team["org_id"] != org_id:
        raise HTTPException(status_code=409, detail="Team already belongs to another org")
    await db.execute("UPDATE teams SET org_id = $1 WHERE id = $2", org_id, team_id)
    await audit(db, user["sub"], "org.team.link", "team", team_id, {"org_id": org_id})
    return {"ok": True}


@router.delete("/orgs/{org_id}/teams/{team_id}", status_code=200)
async def unlink_team_from_org(org_id: str, team_id: str, user: dict = Depends(require_user)):
    await _require_org_admin(org_id, user["sub"])
    db = get_db()
    team = await db.fetchrow("SELECT id, org_id FROM teams WHERE id = $1", team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found")
    if team["org_id"] != org_id:
        raise HTTPException(status_code=400, detail="Team is not linked to this org")
    await require_team_admin(team_id, user["sub"])
    await db.execute("UPDATE teams SET org_id = NULL WHERE id = $1", team_id)
    await audit(db, user["sub"], "org.team.unlink", "team", team_id, {"org_id": org_id})
    return {"ok": True}


# --- Analytics ---


@router.get("/orgs/{org_id}/skills")
async def org_skills(org_id: str, user: dict = Depends(require_user)):
    await _require_org_admin(org_id, user["sub"])
    db = get_db()
    rows = await db.fetch(
        "SELECT s.id, s.name, s.description, s.visibility, s.scope, t.id AS team_id, t.name AS team_name "
        "FROM skills s "
        "JOIN team_skills ts ON s.id = ts.skill_id "
        "JOIN teams t ON ts.team_id = t.id "
        "WHERE t.org_id = $1 "
        "ORDER BY s.name",
        org_id,
    )
    return {
        "skills": [
            {
                "id": r["id"], "name": r["name"], "description": r["description"],
                "visibility": r["visibility"], "scope": r["scope"],
                "team_id": r["team_id"], "team_name": r["team_name"],
            }
            for r in rows
        ]
    }


@router.get("/orgs/{org_id}/usage")
async def org_usage(org_id: str, user: dict = Depends(require_user)):
    await _require_org_admin(org_id, user["sub"])
    db = get_db()
    rows = await db.fetch(
        "SELECT su.id, su.skill_name, su.team_id, su.invoked_at, su.source "
        "FROM skill_usage su "
        "JOIN teams t ON su.team_id = t.id "
        "WHERE t.org_id = $1 "
        "ORDER BY su.invoked_at DESC "
        "LIMIT 500",
        org_id,
    )
    return {
        "usage": [
            {"id": r["id"], "skill_name": r["skill_name"], "team_id": r["team_id"],
             "invoked_at": r["invoked_at"], "source": r["source"]}
            for r in rows
        ]
    }


@router.get("/orgs/{org_id}/usage/summary")
async def org_usage_summary(org_id: str, user: dict = Depends(require_user)):
    await _require_org_admin(org_id, user["sub"])
    db = get_db()
    by_skill = await db.fetch(
        "SELECT su.skill_name, COUNT(*) AS count "
        "FROM skill_usage su "
        "JOIN teams t ON su.team_id = t.id "
        "WHERE t.org_id = $1 "
        "GROUP BY su.skill_name ORDER BY count DESC",
        org_id,
    )
    by_team = await db.fetch(
        "SELECT su.team_id, t.name AS team_name, COUNT(*) AS count "
        "FROM skill_usage su "
        "JOIN teams t ON su.team_id = t.id "
        "WHERE t.org_id = $1 "
        "GROUP BY su.team_id, t.name ORDER BY count DESC",
        org_id,
    )
    return {
        "by_skill": [{"skill_name": r["skill_name"], "count": r["count"]} for r in by_skill],
        "by_team": [{"team_id": r["team_id"], "team_name": r["team_name"], "count": r["count"]} for r in by_team],
    }
