"""Feedback / refine system — lets team members submit feedback on skills."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel

from src.middleware.rate_limit import limiter

from vault.auth_deps import require_user
from vault.audit import audit
from vault.db import get_db
from vault.helpers import require_team_token, resolve_user_from_pat

_FEEDBACK_SELECT = (
    "SELECT f.id, f.skill_id, f.team_id, f.feedback_text, f.status, "
    "f.submitter_team_name, f.created_at, s.name AS skill_name "
    "FROM skill_feedback f LEFT JOIN skills s ON f.skill_id = s.id"
)


def _row_to_dict(r, include_submitter: bool = False) -> dict:
    item = {
        "id": r["id"],
        "skill_id": r["skill_id"],
        "feedback_text": r["feedback_text"],
        "status": r["status"],
        "created_at": r["created_at"],
        "skill_name": r["skill_name"],
    }
    if include_submitter:
        item["team_id"] = r["team_id"]
        item["submitter_team_name"] = r["submitter_team_name"]
    return item


class FeedbackBody(BaseModel):
    feedback_text: str


class StatusBody(BaseModel):
    status: str


async def submit_feedback(
    db, skill_id: str, feedback_text: str,
    team_id: Optional[str] = None,
    submitter_team_name: Optional[str] = None,
) -> dict:
    """Insert a feedback row and return it."""
    feedback_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    await db.execute(
        "INSERT INTO skill_feedback (id, skill_id, team_id, feedback_text, status, submitter_team_name, created_at) "
        "VALUES ($1, $2, $3, $4, 'pending', $5, $6)",
        feedback_id, skill_id, team_id, feedback_text, submitter_team_name, created_at,
    )
    return {
        "id": feedback_id,
        "skill_id": skill_id,
        "team_id": team_id,
        "feedback_text": feedback_text,
        "status": "pending",
        "created_at": created_at,
    }


router = APIRouter(prefix="/api/v1")


@router.post("/skills/{skill_id}/feedback", status_code=201)
@limiter.limit("60/minute")
async def post_feedback(
    request: Request,
    skill_id: str,
    body: FeedbackBody,
    x_team_token: Optional[str] = Header(None, alias="X-Team-Token"),
    x_user_token: Optional[str] = Header(None, alias="X-User-Token"),
):
    # Resolve auth: PAT or legacy team token
    if x_user_token:
        user_info = await resolve_user_from_pat(x_user_token)
        if user_info is None:
            raise HTTPException(status_code=401, detail="Unauthorized")
        first_team = user_info["teams"][0] if user_info["teams"] else {}
        team_id = first_team.get("id")
        team_name = first_team.get("name")
    else:
        team = await require_team_token(x_team_token)
        team_id, team_name = team["id"], team["name"]

    db = get_db()
    row = await db.fetchrow("SELECT id FROM skills WHERE id = $1", skill_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Skill not found")
    return await submit_feedback(
        db, skill_id, body.feedback_text,
        team_id=team_id,
        submitter_team_name=team_name,
    )


@router.post("/teams/{team_id}/skills/{skill_id}/feedback", status_code=201)
async def post_member_feedback(
    team_id: str,
    skill_id: str,
    body: FeedbackBody,
    user: dict = Depends(require_user),
):
    """JWT-authenticated feedback submission for team members."""
    db = get_db()
    # Verify membership
    member = await db.fetchrow(
        "SELECT id FROM team_members WHERE team_id = $1 AND user_id = $2",
        team_id, user["sub"],
    )
    if member is None:
        raise HTTPException(status_code=403, detail="Not a member of this team")
    # Verify skill exists
    skill = await db.fetchrow("SELECT id FROM skills WHERE id = $1", skill_id)
    if skill is None:
        raise HTTPException(status_code=404, detail="Skill not found")
    # Get team name for submitter info
    team = await db.fetchrow("SELECT name FROM teams WHERE id = $1", team_id)
    return await submit_feedback(
        db, skill_id, body.feedback_text,
        team_id=team_id,
        submitter_team_name=team["name"] if team else None,
    )


@router.get("/feedback", dependencies=[Depends(require_user)])
async def get_feedback(
    status: Optional[str] = Query(None),
    include_submitter: bool = Query(False),
):
    db = get_db()
    if status:
        rows = await db.fetch(
            f"{_FEEDBACK_SELECT} WHERE f.status = $1 ORDER BY f.created_at DESC",
            status,
        )
    else:
        rows = await db.fetch(
            f"{_FEEDBACK_SELECT} ORDER BY f.created_at DESC"
        )
    return {"feedback": [_row_to_dict(r, include_submitter) for r in rows]}


@router.patch("/feedback/{feedback_id}")
async def update_feedback_status(feedback_id: str, body: StatusBody, user: dict = Depends(require_user)):
    if body.status not in ("reviewed", "applied"):
        raise HTTPException(status_code=400, detail="Status must be 'reviewed' or 'applied'")
    db = get_db()
    row = await db.fetchrow(
        "SELECT id FROM skill_feedback WHERE id = $1", feedback_id
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Feedback not found")
    await db.execute(
        "UPDATE skill_feedback SET status = $1 WHERE id = $2",
        body.status, feedback_id,
    )
    await audit(db, user["sub"], "feedback.update_status", "feedback", feedback_id, {"status": body.status})
    r = await db.fetchrow(f"{_FEEDBACK_SELECT} WHERE f.id = $1", feedback_id)
    return _row_to_dict(r, include_submitter=True)
