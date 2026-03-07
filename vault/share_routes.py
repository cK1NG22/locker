import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from src.auth import require_user
from vault.audit import audit
from vault.db import get_db

router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_user)])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ShareRequestCreate(BaseModel):
    skill_id: str
    from_team_id: str
    to_team_id: str


class ShareRequestResolve(BaseModel):
    status: str  # "approved" or "denied"


@router.post("/share-requests", status_code=201)
async def create_share_request(body: ShareRequestCreate, user: dict = Depends(require_user)):
    db = get_db()
    user_id = user["sub"]

    # Verify both teams exist and belong to the same org
    from_team = await db.fetchrow("SELECT id, org_id FROM teams WHERE id = $1", body.from_team_id)
    to_team = await db.fetchrow("SELECT id, org_id FROM teams WHERE id = $1", body.to_team_id)
    if from_team is None:
        raise HTTPException(status_code=404, detail="Source team not found")
    if to_team is None:
        raise HTTPException(status_code=404, detail="Target team not found")
    if from_team["org_id"] is None or to_team["org_id"] is None:
        raise HTTPException(status_code=400, detail="Both teams must belong to an org")
    if from_team["org_id"] != to_team["org_id"]:
        raise HTTPException(status_code=400, detail="Both teams must belong to the same org")

    # Require org admin
    from vault.org_routes import _require_org_admin
    await _require_org_admin(from_team["org_id"], user_id)

    # Verify skill exists and is assigned to from_team
    skill = await db.fetchrow(
        "SELECT 1 FROM team_skills WHERE team_id = $1 AND skill_id = $2",
        body.from_team_id, body.skill_id,
    )
    if skill is None:
        raise HTTPException(status_code=404, detail="Skill not found in source team")

    req_id = str(uuid.uuid4())
    now = _now()
    await db.execute(
        "INSERT INTO skill_share_requests (id, skill_id, from_team_id, to_team_id, requested_by, status, created_at) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7)",
        req_id, body.skill_id, body.from_team_id, body.to_team_id, user_id, "pending", now,
    )
    await audit(db, user_id, "share_request.create", "share_request", req_id,
                {"skill_id": body.skill_id, "from_team_id": body.from_team_id, "to_team_id": body.to_team_id})
    return {"id": req_id, "status": "pending", "created_at": now}


@router.get("/share-requests")
async def list_share_requests(
    team_id: Optional[str] = Query(None),
    user: dict = Depends(require_user),
):
    db = get_db()
    if team_id:
        # Require team admin to view requests
        from vault.team_routes import _require_team_admin
        await _require_team_admin(team_id, user["sub"])
        rows = await db.fetch(
            "SELECT sr.id, sr.skill_id, s.name AS skill_name, sr.from_team_id, ft.name AS from_team_name, "
            "sr.to_team_id, tt.name AS to_team_name, sr.requested_by, sr.status, sr.created_at, sr.resolved_at "
            "FROM skill_share_requests sr "
            "JOIN skills s ON sr.skill_id = s.id "
            "JOIN teams ft ON sr.from_team_id = ft.id "
            "JOIN teams tt ON sr.to_team_id = tt.id "
            "WHERE sr.to_team_id = $1 AND sr.status = 'pending' "
            "ORDER BY sr.created_at DESC",
            team_id,
        )
    else:
        rows = await db.fetch(
            "SELECT sr.id, sr.skill_id, s.name AS skill_name, sr.from_team_id, ft.name AS from_team_name, "
            "sr.to_team_id, tt.name AS to_team_name, sr.requested_by, sr.status, sr.created_at, sr.resolved_at "
            "FROM skill_share_requests sr "
            "JOIN skills s ON sr.skill_id = s.id "
            "JOIN teams ft ON sr.from_team_id = ft.id "
            "JOIN teams tt ON sr.to_team_id = tt.id "
            "ORDER BY sr.created_at DESC "
            "LIMIT 100",
        )
    return {
        "requests": [
            {
                "id": r["id"], "skill_id": r["skill_id"], "skill_name": r["skill_name"],
                "from_team_id": r["from_team_id"], "from_team_name": r["from_team_name"],
                "to_team_id": r["to_team_id"], "to_team_name": r["to_team_name"],
                "requested_by": r["requested_by"], "status": r["status"],
                "created_at": r["created_at"], "resolved_at": r["resolved_at"],
            }
            for r in rows
        ]
    }


@router.patch("/share-requests/{request_id}")
async def resolve_share_request(request_id: str, body: ShareRequestResolve, user: dict = Depends(require_user)):
    if body.status not in ("approved", "denied"):
        raise HTTPException(status_code=422, detail="Status must be 'approved' or 'denied'")

    db = get_db()
    row = await db.fetchrow(
        "SELECT id, skill_id, from_team_id, to_team_id, status FROM skill_share_requests WHERE id = $1",
        request_id,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Share request not found")
    if row["status"] != "pending":
        raise HTTPException(status_code=400, detail="Request already resolved")

    # Require team admin of the target team
    from vault.team_routes import _require_team_admin
    await _require_team_admin(row["to_team_id"], user["sub"])

    now = _now()
    await db.execute(
        "UPDATE skill_share_requests SET status = $1, resolved_at = $2, resolved_by = $3 WHERE id = $4",
        body.status, now, user["sub"], request_id,
    )

    if body.status == "approved":
        # Link (not copy) the skill to the target team
        existing = await db.fetchrow(
            "SELECT 1 FROM team_skills WHERE team_id = $1 AND skill_id = $2",
            row["to_team_id"], row["skill_id"],
        )
        if existing is None:
            await db.execute(
                "INSERT INTO team_skills (team_id, skill_id) VALUES ($1, $2)",
                row["to_team_id"], row["skill_id"],
            )

    await audit(db, user["sub"], f"share_request.{body.status}", "share_request", request_id,
                {"skill_id": row["skill_id"], "to_team_id": row["to_team_id"]})
    return {"id": request_id, "status": body.status, "resolved_at": now}
