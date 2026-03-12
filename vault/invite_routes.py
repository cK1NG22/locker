import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request

from vault.auth_deps import require_user
from vault.audit import audit
from vault.crypto import decrypt
from vault.db import get_db
from vault.helpers import utc_now
from src.middleware.rate_limit import limiter

_BASE_URL = os.environ.get("LOCKER_BASE_URL", "https://locker.up.railway.app")

router = APIRouter(prefix="/api/v1/invite")


@router.get("/{slug}")
async def get_invite_info(slug: str):
    """Public — no auth required. Returns team info for the invite page."""
    db = get_db()
    row = await db.fetchrow(
        "SELECT t.id, t.name, t.slug FROM teams t WHERE t.slug = $1", slug
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Team not found")

    skill_count = await db.fetchval(
        "SELECT COUNT(*) FROM team_skills WHERE team_id = $1", row["id"]
    )
    member_count = await db.fetchval(
        "SELECT COUNT(*) FROM team_members WHERE team_id = $1", row["id"]
    )
    return {
        "name": row["name"],
        "slug": row["slug"],
        "skill_count": skill_count,
        "member_count": member_count,
    }


@router.post("/{slug}/join")
async def join_team(slug: str, user: dict = Depends(require_user)):
    """Requires Bearer JWT. Adds user to team, returns setup info."""
    db = get_db()
    row = await db.fetchrow(
        "SELECT id, name, token_encrypted, invite_code FROM teams WHERE slug = $1", slug
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Team not found")

    team_id = row["id"]
    user_id = user["sub"]

    # Check if already a member
    existing = await db.fetchrow(
        "SELECT id FROM team_members WHERE team_id = $1 AND user_id = $2",
        team_id, user_id,
    )

    cli_command = None
    if row["invite_code"]:
        cli_command = f"locker join {row['invite_code']}"

    if existing:
        # Already a member — still return setup info (409 with data)
        return {
            "team_id": team_id,
            "team_name": row["name"],
            "cli_command": cli_command,
            "already_member": True,
        }

    # Add as member
    member_id = str(uuid.uuid4())
    now = utc_now()
    await db.execute(
        "INSERT INTO team_members (id, team_id, user_id, role, can_share, created_at) VALUES ($1, $2, $3, $4, $5, $6)",
        member_id, team_id, user_id, "member", False, now,
    )
    await audit(db, user_id, "invite.join", "team", team_id, {"slug": slug})

    return {
        "team_id": team_id,
        "team_name": row["name"],
        "cli_command": cli_command,
        "already_member": False,
    }


@router.get("/{slug}/setup")
async def get_setup_command(slug: str, user: dict = Depends(require_user)):
    """Requires Bearer JWT + team membership. Returns CLI command."""
    db = get_db()
    row = await db.fetchrow(
        "SELECT id, name, invite_code FROM teams WHERE slug = $1", slug
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Team not found")

    # Verify membership
    member = await db.fetchrow(
        "SELECT id FROM team_members WHERE team_id = $1 AND user_id = $2",
        row["id"], user["sub"],
    )
    if member is None:
        raise HTTPException(status_code=403, detail="Not a member of this team")

    if not row["invite_code"]:
        raise HTTPException(status_code=404, detail="Invite code not available — ask a team admin to regenerate it")

    return {
        "cli_command": f"locker join {row['invite_code']}",
    }


@router.post("/join-cli")
@limiter.limit("5/minute")
async def join_cli(request: Request):
    """Public — no auth. Validates invite code, returns team info for CLI setup."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid JSON body")

    invite_code = (body.get("invite_code") or "").strip().upper()
    if not invite_code:
        raise HTTPException(status_code=422, detail="invite_code is required")

    db = get_db()
    row = await db.fetchrow(
        "SELECT id, name, token_encrypted FROM teams WHERE invite_code = $1",
        invite_code,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Invalid invite code")

    if not row["token_encrypted"]:
        raise HTTPException(
            status_code=404,
            detail="Team setup incomplete — ask admin to rotate the team token",
        )

    try:
        team_token = decrypt(row["token_encrypted"])
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to decrypt team token — contact admin",
        )

    skill_count = await db.fetchval(
        "SELECT COUNT(*) FROM team_skills WHERE team_id = $1", row["id"]
    )

    return {
        "team_name": row["name"],
        "team_token": team_token,
        "server_url": _BASE_URL,
        "skill_count": skill_count,
    }
