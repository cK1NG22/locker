import re
import uuid

from asyncpg import UniqueViolationError
from fastapi import APIRouter, Depends, HTTPException

from vault.auth_deps import require_user
from vault.audit import audit
from vault.db import get_db
from vault.helpers import utc_now, require_team_admin
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
    MyTeam,
    MemberSkill,
    TeamJoin,
    TeamJoinResult,
    PersonalToken,
)
from vault.crypto import encrypt, decrypt
from vault.token_utils import generate_token, generate_invite_code, generate_pat

router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_user)])


async def _unique_invite_code(db, name: str) -> str:
    """Generate an invite code, retrying on collision."""
    code = generate_invite_code(name)
    while await db.fetchval("SELECT 1 FROM teams WHERE invite_code = $1", code):
        code = generate_invite_code(name)
    return code


def slugify(name: str) -> str:
    """Convert team name to URL-friendly slug."""
    slug = name.lower().strip()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    return slug.strip('-')


async def _require_membership(db, team_id: str, user_id: str) -> None:
    """Raise 403 if user is not a member of the team."""
    row = await db.fetchrow(
        "SELECT id FROM team_members WHERE team_id = $1 AND user_id = $2",
        team_id, user_id,
    )
    if row is None:
        raise HTTPException(status_code=403, detail="Not a member of this team")


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
    token_enc = encrypt(plaintext)
    slug = slugify(body.name)
    now = utc_now()
    user_id = user["sub"]
    db = get_db()
    invite_code = await _unique_invite_code(db, body.name)

    async with db.acquire() as conn:
        async with conn.transaction():
            try:
                await conn.execute(
                    "INSERT INTO teams (id, name, slug, token_hash, token_prefix, token_encrypted, invite_code, owner_id, created_at) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)",
                    team_id, body.name, slug, token_hash, token_prefix, token_enc, invite_code, user_id, now,
                )
            except UniqueViolationError:
                raise HTTPException(status_code=409, detail=f"Team '{body.name}' already exists")
            await conn.execute(
                "INSERT INTO team_members (id, team_id, user_id, role, can_share, created_at) VALUES ($1, $2, $3, $4, $5, $6)",
                member_id, team_id, user_id, "admin", True, now,
            )
    await audit(db, user["sub"], "team.create", "team", team_id, {"name": body.name})
    return TeamCreated(id=team_id, name=body.name, slug=slug, token=plaintext, token_prefix=token_prefix, invite_code=invite_code, owner_id=user_id, created_at=now)


@router.get("/teams", response_model=list[TeamSummary])
async def list_teams(user: dict = Depends(require_user)):
    db = get_db()
    user_id = user["sub"]
    rows = await db.fetch(
        "SELECT t.id, t.name, t.slug, COUNT(ts.skill_id) AS skill_count "
        "FROM teams t LEFT JOIN team_skills ts ON t.id = ts.team_id "
        "WHERE t.id IN ("
        "  SELECT tm.team_id FROM team_members tm WHERE tm.user_id = $1"
        "  UNION"
        "  SELECT t2.id FROM teams t2 JOIN org_members om ON t2.org_id = om.org_id WHERE om.user_id = $1"
        ") "
        "GROUP BY t.id, t.name, t.slug",
        user_id,
    )
    return [
        TeamSummary(id=row["id"], name=row["name"], slug=row["slug"], skill_count=row["skill_count"])
        for row in rows
    ]


@router.get("/me/teams", response_model=list[MyTeam])
async def my_teams(user: dict = Depends(require_user)):
    """Return all teams the user belongs to with their role in each."""
    db = get_db()
    user_id = user["sub"]
    rows = await db.fetch(
        "SELECT t.id, t.name, t.slug, tm.role, tm.can_share, "
        "COUNT(ts.skill_id) AS skill_count "
        "FROM team_members tm "
        "JOIN teams t ON tm.team_id = t.id "
        "LEFT JOIN team_skills ts ON t.id = ts.team_id "
        "WHERE tm.user_id = $1 "
        "GROUP BY t.id, t.name, t.slug, tm.role, tm.can_share",
        user_id,
    )
    return [
        MyTeam(
            team_id=r["id"], team_name=r["name"], slug=r["slug"],
            role=r["role"], can_share=bool(r["can_share"]),
            skill_count=r["skill_count"],
        )
        for r in rows
    ]


@router.get("/teams/{team_id}", response_model=TeamDetail)
async def get_team(team_id: str, user: dict = Depends(require_user)):
    db = get_db()
    row = await db.fetchrow(
        "SELECT id, name, slug, token_prefix, invite_code, owner_id, created_at FROM teams WHERE id = $1", team_id
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Team not found")
    await _require_membership(db, team_id, user["sub"])
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
        slug=row["slug"],
        token_prefix=row["token_prefix"],
        invite_code=row["invite_code"],
        owner_id=row["owner_id"],
        created_at=row["created_at"],
        skills=skill_names,
        members=members,
    )


@router.get("/teams/{team_id}/member-skills", response_model=list[MemberSkill])
async def get_member_skills(team_id: str, user: dict = Depends(require_user)):
    """Member skill browsing — returns visible skills for team members."""
    db = get_db()
    await _require_membership(db, team_id, user["sub"])
    rows = await db.fetch(
        "SELECT s.id, s.name, s.description, s.visibility, s.content FROM skills s "
        "JOIN team_skills ts ON s.id = ts.skill_id "
        "WHERE ts.team_id = $1 AND s.visibility != 'hidden' AND s.scope = 'team'",
        team_id,
    )
    skills = []
    for row in rows:
        content = decrypt(row["content"]) if row["visibility"] == "open" else None
        skills.append(MemberSkill(
            id=row["id"], name=row["name"], description=row["description"],
            visibility=row["visibility"], content=content,
        ))
    return skills


@router.put("/teams/{team_id}", response_model=TeamOut)
async def update_team(team_id: str, body: TeamUpdate, user: dict = Depends(require_user)):
    await require_team_admin(team_id, user["sub"])
    db = get_db()
    row = await db.fetchrow(
        "SELECT id, name, token_prefix, invite_code, owner_id, created_at FROM teams WHERE id = $1", team_id
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Team not found")
    slug = slugify(body.name)
    try:
        await db.execute(
            "UPDATE teams SET name = $1, slug = $2 WHERE id = $3", body.name, slug, team_id
        )
    except UniqueViolationError:
        raise HTTPException(status_code=409, detail=f"Team '{body.name}' already exists")
    await audit(db, user["sub"], "team.update", "team", team_id, {"name": body.name})
    return TeamOut(
        id=row["id"], name=body.name, slug=slug, token_prefix=row["token_prefix"], invite_code=row["invite_code"], owner_id=row["owner_id"], created_at=row["created_at"]
    )


@router.delete("/teams/{team_id}", status_code=204)
async def delete_team(team_id: str, user: dict = Depends(require_user)):
    await require_team_admin(team_id, user["sub"])
    db = get_db()
    await db.execute("DELETE FROM teams WHERE id = $1", team_id)
    await audit(db, user["sub"], "team.delete", "team", team_id)


@router.post("/teams/{team_id}/rotate-token", response_model=TeamCreated)
async def rotate_token(team_id: str, user: dict = Depends(require_user)):
    await require_team_admin(team_id, user["sub"])
    db = get_db()
    row = await db.fetchrow(
        "SELECT id, name, slug, invite_code, owner_id, created_at FROM teams WHERE id = $1", team_id
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Team not found")
    plaintext, token_hash, token_prefix = generate_token()
    token_enc = encrypt(plaintext)
    await db.execute(
        "UPDATE teams SET token_hash = $1, token_prefix = $2, token_encrypted = $3 WHERE id = $4",
        token_hash, token_prefix, token_enc, team_id,
    )
    return TeamCreated(
        id=row["id"], name=row["name"], slug=row["slug"], token=plaintext, token_prefix=token_prefix,
        invite_code=row["invite_code"], owner_id=row["owner_id"], created_at=row["created_at"],
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
    await audit(db, user["sub"], "team.assign_skills", "team", team_id, {"skill_ids": body.skill_ids})
    return {"ok": True}


@router.post("/teams/{team_id}/members", status_code=201, response_model=TeamMemberOut)
async def add_member(team_id: str, body: TeamMemberAdd, user: dict = Depends(require_user)):
    await require_team_admin(team_id, user["sub"])
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
    now = utc_now()
    await db.execute(
        "INSERT INTO team_members (id, team_id, user_id, role, can_share, created_at) VALUES ($1, $2, $3, $4, $5, $6)",
        member_id, team_id, target_user_id, "member", False, now,
    )
    await audit(db, user["sub"], "member.add", "member", member_id, {"team_id": team_id, "email": body.email, "role": "member"})
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
    await require_team_admin(team_id, user["sub"])
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
    await audit(db, user["sub"], "member.update", "member", member_id, {"team_id": team_id, "role": new_role, "can_share": bool(new_can_share)})
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
    await require_team_admin(team_id, user["sub"])
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
    await audit(db, user["sub"], "member.remove", "member", member_id, {"team_id": team_id})


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
    now = utc_now()
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

    await audit(db, user["sub"], "skill.copy_to_team", "skill", new_skill_id, {"source_skill_id": skill_id, "target_team_id": target_team_id})
    return SkillCopied(id=new_skill_id, name=skill["name"], target_team_id=target_team_id, created_at=now)


# ============================================================
# Invite code endpoints
# ============================================================


@router.post("/teams/join", response_model=TeamJoinResult)
async def join_team(body: TeamJoin, user: dict = Depends(require_user)):
    db = get_db()
    code = body.invite_code.strip().upper()
    team_row = await db.fetchrow(
        "SELECT id, name FROM teams WHERE invite_code = $1", code
    )
    if team_row is None:
        raise HTTPException(status_code=404, detail="Invalid invite code")
    user_id = user["sub"]
    team_id = team_row["id"]

    # Check if already a member
    existing = await db.fetchrow(
        "SELECT id FROM team_members WHERE team_id = $1 AND user_id = $2",
        team_id, user_id,
    )
    if existing:
        return TeamJoinResult(team_id=team_id, team_name=team_row["name"], already_member=True)

    # Add as member
    member_id = str(uuid.uuid4())
    now = utc_now()
    await db.execute(
        "INSERT INTO team_members (id, team_id, user_id, role, can_share, created_at) VALUES ($1, $2, $3, $4, $5, $6)",
        member_id, team_id, user_id, "member", False, now,
    )

    # Generate PAT if user doesn't have one
    pat_plaintext = None
    existing_pat = await db.fetchrow(
        "SELECT id FROM user_tokens WHERE user_id = $1 AND revoked_at IS NULL", user_id
    )
    if not existing_pat:
        plaintext, pat_hash, pat_prefix = generate_pat()
        pat_id = str(uuid.uuid4())
        await db.execute(
            "INSERT INTO user_tokens (id, user_id, token_hash, token_prefix, name, created_at) VALUES ($1, $2, $3, $4, $5, $6)",
            pat_id, user_id, pat_hash, pat_prefix, "default", now,
        )
        pat_plaintext = plaintext

    await audit(db, user["sub"], "team.join", "team", team_id, {"invite_code": code})
    return TeamJoinResult(team_id=team_id, team_name=team_row["name"], already_member=False, personal_token=pat_plaintext)


@router.post("/teams/{team_id}/regenerate-invite-code")
async def regenerate_invite_code_endpoint(team_id: str, user: dict = Depends(require_user)):
    await require_team_admin(team_id, user["sub"])
    db = get_db()
    row = await db.fetchrow("SELECT name FROM teams WHERE id = $1", team_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Team not found")
    code = await _unique_invite_code(db, row["name"])
    await db.execute("UPDATE teams SET invite_code = $1 WHERE id = $2", code, team_id)
    await audit(db, user["sub"], "team.regenerate_invite_code", "team", team_id, {"invite_code": code})
    return {"invite_code": code}


# ============================================================
# Personal Access Token (PAT) management
# ============================================================


@router.get("/me/tokens", response_model=list[PersonalToken])
async def list_tokens(user: dict = Depends(require_user)):
    db = get_db()
    rows = await db.fetch(
        "SELECT id, token_prefix, name, created_at FROM user_tokens "
        "WHERE user_id = $1 AND revoked_at IS NULL ORDER BY created_at DESC",
        user["sub"],
    )
    return [
        PersonalToken(id=r["id"], prefix=r["token_prefix"], name=r["name"], created_at=r["created_at"])
        for r in rows
    ]


@router.post("/me/tokens", status_code=201)
async def create_token(user: dict = Depends(require_user)):
    db = get_db()
    plaintext, pat_hash, pat_prefix = generate_pat()
    pat_id = str(uuid.uuid4())
    now = utc_now()
    # Count existing active tokens to name them
    count = await db.fetchval(
        "SELECT COUNT(*) FROM user_tokens WHERE user_id = $1 AND revoked_at IS NULL",
        user["sub"],
    )
    name = "default" if count == 0 else f"token-{count + 1}"
    await db.execute(
        "INSERT INTO user_tokens (id, user_id, token_hash, token_prefix, name, created_at) VALUES ($1, $2, $3, $4, $5, $6)",
        pat_id, user["sub"], pat_hash, pat_prefix, name, now,
    )
    return {"id": pat_id, "token": plaintext, "prefix": pat_prefix, "name": name, "created_at": now}


@router.delete("/me/tokens/{token_id}", status_code=204)
async def revoke_token(token_id: str, user: dict = Depends(require_user)):
    db = get_db()
    row = await db.fetchrow(
        "SELECT id FROM user_tokens WHERE id = $1 AND user_id = $2 AND revoked_at IS NULL",
        token_id, user["sub"],
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Token not found")
    now = utc_now()
    await db.execute("UPDATE user_tokens SET revoked_at = $1 WHERE id = $2", now, token_id)
