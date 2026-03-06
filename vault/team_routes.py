import uuid
from datetime import datetime, timezone

from asyncpg import UniqueViolationError
from fastapi import APIRouter, Depends, HTTPException

from src.auth import require_user
from vault.db import get_db
from vault.models import (
    TeamCreate,
    TeamUpdate,
    TeamOut,
    TeamCreated,
    TeamSummary,
    TeamDetail,
    TeamMemberOut,
    TeamMemberUpdate,
    TeamMemberAdd,
    TeamSkillsSet,
    SkillCopied,
)
from vault.token_utils import generate_token

router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_user)])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _require_team_admin(team_id: str, user_id: str) -> None:
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


async def _require_team_share(team_id: str, user_id: str) -> None:
    """Raise 403 if user is not an admin and does not have can_share permission."""
    db = get_db()
    row = await db.fetchrow("SELECT owner_id FROM teams WHERE id = $1", team_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Team not found")
    if row["owner_id"] is None:
        return
    member = await db.fetchrow(
        "SELECT role, can_share FROM team_members WHERE team_id = $1 AND user_id = $2",
        team_id, user_id,
    )
    if member is None:
        raise HTTPException(status_code=403, detail="Team share access required")
    if member["role"] == "admin" or member["can_share"]:
        return
    raise HTTPException(status_code=403, detail="Team share access required")


@router.post("/teams", status_code=201, response_model=TeamCreated)
async def create_team(body: TeamCreate, user: dict = Depends(require_user)):
    team_id = str(uuid.uuid4())
    member_id = str(uuid.uuid4())
    plaintext, token_hash, token_prefix = generate_token()
    now = _now()
    user_id = user["sub"]
    db = get_db()
    async with db.acquire() as conn:
        async with conn.transaction():
            try:
                await conn.execute(
                    "INSERT INTO teams (id, name, token_hash, token_prefix, owner_id, created_at) VALUES ($1, $2, $3, $4, $5, $6)",
                    team_id, body.name, token_hash, token_prefix, user_id, now,
                )
            except UniqueViolationError:
                raise HTTPException(status_code=409, detail=f"Team '{body.name}' already exists")
            await conn.execute(
                "INSERT INTO team_members (id, team_id, user_id, role, can_share, created_at) VALUES ($1, $2, $3, $4, $5, $6)",
                member_id, team_id, user_id, "admin", True, now,
            )
    return TeamCreated(id=team_id, name=body.name, token=plaintext, token_prefix=token_prefix, owner_id=user_id, created_at=now)


@router.get("/teams", response_model=list[TeamSummary])
async def list_teams():
    db = get_db()
    rows = await db.fetch(
        "SELECT t.id, t.name, COUNT(ts.skill_id) AS skill_count "
        "FROM teams t LEFT JOIN team_skills ts ON t.id = ts.team_id "
        "GROUP BY t.id, t.name"
    )
    return [
        TeamSummary(id=row["id"], name=row["name"], skill_count=row["skill_count"])
        for row in rows
    ]


@router.get("/teams/{team_id}", response_model=TeamDetail)
async def get_team(team_id: str):
    db = get_db()
    row = await db.fetchrow(
        "SELECT id, name, token_prefix, owner_id, created_at FROM teams WHERE id = $1", team_id
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Team not found")
    skill_rows = await db.fetch(
        "SELECT s.name FROM skills s JOIN team_skills ts ON s.id = ts.skill_id WHERE ts.team_id = $1",
        team_id,
    )
    skill_names = [r["name"] for r in skill_rows]
    member_rows = await db.fetch(
        "SELECT tm.id, tm.user_id, u.email, u.name, tm.role, tm.can_share, tm.created_at "
        "FROM team_members tm LEFT JOIN users u ON tm.user_id = u.id "
        "WHERE tm.team_id = $1",
        team_id,
    )
    members = [
        TeamMemberOut(
            id=r["id"],
            user_id=r["user_id"],
            email=r["email"],
            name=r["name"],
            role=r["role"],
            can_share=bool(r["can_share"]),
            created_at=r["created_at"],
        )
        for r in member_rows
    ]
    return TeamDetail(
        id=row["id"],
        name=row["name"],
        token_prefix=row["token_prefix"],
        owner_id=row["owner_id"],
        created_at=row["created_at"],
        skills=skill_names,
        members=members,
    )


@router.put("/teams/{team_id}", response_model=TeamOut)
async def update_team(team_id: str, body: TeamUpdate, user: dict = Depends(require_user)):
    await _require_team_admin(team_id, user["sub"])
    db = get_db()
    row = await db.fetchrow(
        "SELECT id, name, token_prefix, owner_id, created_at FROM teams WHERE id = $1", team_id
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Team not found")
    try:
        await db.execute(
            "UPDATE teams SET name = $1 WHERE id = $2", body.name, team_id
        )
    except UniqueViolationError:
        raise HTTPException(status_code=409, detail=f"Team '{body.name}' already exists")
    return TeamOut(
        id=row["id"], name=body.name, token_prefix=row["token_prefix"], owner_id=row["owner_id"], created_at=row["created_at"]
    )


@router.delete("/teams/{team_id}", status_code=204)
async def delete_team(team_id: str, user: dict = Depends(require_user)):
    await _require_team_admin(team_id, user["sub"])
    db = get_db()
    await db.execute("DELETE FROM teams WHERE id = $1", team_id)


@router.post("/teams/{team_id}/rotate-token", response_model=TeamCreated)
async def rotate_token(team_id: str, user: dict = Depends(require_user)):
    await _require_team_admin(team_id, user["sub"])
    db = get_db()
    row = await db.fetchrow(
        "SELECT id, name, owner_id, created_at FROM teams WHERE id = $1", team_id
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Team not found")
    plaintext, token_hash, token_prefix = generate_token()
    await db.execute(
        "UPDATE teams SET token_hash = $1, token_prefix = $2 WHERE id = $3",
        token_hash, token_prefix, team_id,
    )
    return TeamCreated(
        id=row["id"], name=row["name"], token=plaintext, token_prefix=token_prefix,
        owner_id=row["owner_id"], created_at=row["created_at"],
    )


@router.put("/teams/{team_id}/skills", status_code=200)
async def set_team_skills(team_id: str, body: TeamSkillsSet, user: dict = Depends(require_user)):
    await _require_team_share(team_id, user["sub"])
    db = get_db()
    row = await db.fetchrow("SELECT id FROM teams WHERE id = $1", team_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Team not found")
    # Validate all skill IDs exist
    for sid in body.skill_ids:
        c = await db.fetchrow("SELECT id FROM skills WHERE id = $1", sid)
        if c is None:
            raise HTTPException(status_code=404, detail=f"Skill '{sid}' not found")
    # Replace all assignments
    async with db.acquire() as conn:
        async with conn.transaction():
            await conn.execute("DELETE FROM team_skills WHERE team_id = $1", team_id)
            for sid in body.skill_ids:
                await conn.execute(
                    "INSERT INTO team_skills (team_id, skill_id) VALUES ($1, $2)",
                    team_id, sid,
                )
    return {"ok": True}


@router.post("/teams/{team_id}/members", status_code=201, response_model=TeamMemberOut)
async def add_member(team_id: str, body: TeamMemberAdd, user: dict = Depends(require_user)):
    await _require_team_admin(team_id, user["sub"])
    db = get_db()
    # Look up user by email
    user_row = await db.fetchrow("SELECT id, email, name FROM users WHERE email = $1", body.email)
    if user_row is None:
        raise HTTPException(status_code=404, detail=f"User '{body.email}' not found")
    target_user_id = user_row["id"]
    # Check for duplicate membership
    dup = await db.fetchrow(
        "SELECT id FROM team_members WHERE team_id = $1 AND user_id = $2",
        team_id, target_user_id,
    )
    if dup is not None:
        raise HTTPException(status_code=409, detail="User is already a member of this team")
    member_id = str(uuid.uuid4())
    now = _now()
    await db.execute(
        "INSERT INTO team_members (id, team_id, user_id, role, can_share, created_at) VALUES ($1, $2, $3, $4, $5, $6)",
        member_id, team_id, target_user_id, "member", False, now,
    )
    return TeamMemberOut(
        id=member_id,
        user_id=target_user_id,
        email=user_row["email"],
        name=user_row["name"],
        role="member",
        can_share=False,
        created_at=now,
    )


@router.patch("/teams/{team_id}/members/{member_id}", response_model=TeamMemberOut)
async def update_member(
    team_id: str, member_id: str, body: TeamMemberUpdate, user: dict = Depends(require_user)
):
    await _require_team_admin(team_id, user["sub"])
    if body.role is None and body.can_share is None:
        raise HTTPException(status_code=422, detail="At least one field required")
    db = get_db()
    row = await db.fetchrow(
        "SELECT tm.id, tm.user_id, u.email, u.name, tm.role, tm.can_share, tm.created_at "
        "FROM team_members tm LEFT JOIN users u ON tm.user_id = u.id "
        "WHERE tm.id = $1 AND tm.team_id = $2",
        member_id, team_id,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Member not found")
    new_role = body.role if body.role is not None else row["role"]
    new_can_share = body.can_share if body.can_share is not None else row["can_share"]
    # Prevent removing the last admin
    if row["role"] == "admin" and new_role != "admin":
        count_row = await db.fetchrow(
            "SELECT COUNT(*) AS cnt FROM team_members WHERE team_id = $1 AND role = 'admin'",
            team_id,
        )
        if count_row["cnt"] <= 1:
            raise HTTPException(status_code=400, detail="Cannot remove the last team admin")
    await db.execute(
        "UPDATE team_members SET role = $1, can_share = $2 WHERE id = $3",
        new_role, new_can_share, member_id,
    )
    return TeamMemberOut(
        id=row["id"],
        user_id=row["user_id"],
        email=row["email"],
        name=row["name"],
        role=new_role,
        can_share=bool(new_can_share),
        created_at=row["created_at"],
    )


@router.delete("/teams/{team_id}/members/{member_id}", status_code=204)
async def remove_member(team_id: str, member_id: str, user: dict = Depends(require_user)):
    await _require_team_admin(team_id, user["sub"])
    db = get_db()
    row = await db.fetchrow(
        "SELECT tm.user_id, tm.role FROM team_members tm WHERE tm.id = $1 AND tm.team_id = $2",
        member_id, team_id,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Member not found")
    # Prevent removing the team owner
    owner_row = await db.fetchrow("SELECT owner_id FROM teams WHERE id = $1", team_id)
    if owner_row and row["user_id"] == owner_row["owner_id"]:
        raise HTTPException(status_code=400, detail="Cannot remove the team owner")
    # Prevent removing the last admin
    if row["role"] == "admin":
        count_row = await db.fetchrow(
            "SELECT COUNT(*) AS cnt FROM team_members WHERE team_id = $1 AND role = 'admin'",
            team_id,
        )
        if count_row["cnt"] <= 1:
            raise HTTPException(status_code=400, detail="Cannot remove the last team admin")
    await db.execute("DELETE FROM team_members WHERE id = $1 AND team_id = $2", member_id, team_id)


@router.post("/skills/{skill_id}/copy-to-team/{target_team_id}", status_code=201, response_model=SkillCopied)
async def copy_skill_to_team(skill_id: str, target_team_id: str, user: dict = Depends(require_user)):
    user_id = user["sub"]
    db = get_db()

    # 1. Get source skill
    skill = await db.fetchrow(
        "SELECT id, name, content, description, visibility, scope, uploaded_by FROM skills WHERE id = $1",
        skill_id,
    )
    if skill is None:
        raise HTTPException(status_code=404, detail="Skill not found")

    # 2. Eligibility check
    eligible = False
    if skill["scope"] == "personal" and skill["uploaded_by"] == user_id:
        eligible = True
    elif skill["scope"] == "team" and skill["visibility"] == "open":
        # User must be a member of at least one team that has this skill
        mc = await db.fetchrow(
            "SELECT 1 FROM team_skills ts JOIN team_members tm ON ts.team_id = tm.team_id "
            "WHERE ts.skill_id = $1 AND tm.user_id = $2",
            skill_id, user_id,
        )
        if mc is not None:
            eligible = True

    if not eligible:
        raise HTTPException(status_code=403, detail="Not eligible to copy this skill")

    # 3. Check user is a member of the target team
    mc = await db.fetchrow(
        "SELECT 1 FROM team_members WHERE team_id = $1 AND user_id = $2",
        target_team_id, user_id,
    )
    if mc is None:
        raise HTTPException(status_code=403, detail="You are not a member of the target team")

    # 4. Check can_share permission in target team (reuses existing helper)
    await _require_team_share(target_team_id, user_id)

    # 5. Check name uniqueness in target team
    nc = await db.fetchrow(
        "SELECT 1 FROM skills s JOIN team_skills ts ON s.id = ts.skill_id "
        "WHERE s.name = $1 AND ts.team_id = $2",
        skill["name"], target_team_id,
    )
    if nc is not None:
        raise HTTPException(
            status_code=409,
            detail=f"A skill named '{skill['name']}' already exists in the target team",
        )

    # 6. Copy skill record + files + link in a transaction
    now = _now()
    new_skill_id = str(uuid.uuid4())
    file_rows = await db.fetch(
        "SELECT path, content, size_bytes FROM skill_files WHERE skill_id = $1",
        skill_id,
    )
    async with db.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "INSERT INTO skills (id, name, content, description, visibility, scope, uploaded_by, created_at, updated_at) "
                "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)",
                new_skill_id, skill["name"], skill["content"], skill["description"],
                skill["visibility"], "team", user_id, now, now,
            )
            for fr in file_rows:
                await conn.execute(
                    "INSERT INTO skill_files (id, skill_id, path, content, size_bytes, created_at) VALUES ($1, $2, $3, $4, $5, $6)",
                    str(uuid.uuid4()), new_skill_id, fr["path"], fr["content"], fr["size_bytes"], now,
                )
            await conn.execute(
                "INSERT INTO team_skills (team_id, skill_id) VALUES ($1, $2)",
                target_team_id, new_skill_id,
            )

    return SkillCopied(id=new_skill_id, name=skill["name"], target_team_id=target_team_id, created_at=now)
