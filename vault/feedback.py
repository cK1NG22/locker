"""Feedback / refine system — lets team members submit feedback on skills."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel

from src.middleware.rate_limit import limiter

from src.auth import require_user
from vault.db import get_db
from vault.token_utils import hash_token


class FeedbackBody(BaseModel):
    feedback_text: str


class StatusBody(BaseModel):
    status: str


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


async def submit_feedback(db, skill_id: str, feedback_text: str, team_id: Optional[str] = None) -> dict:
    """Insert a feedback row and return it."""
    feedback_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    await db.execute(
        "INSERT INTO skill_feedback (id, skill_id, team_id, feedback_text, status, created_at) "
        "VALUES ($1, $2, $3, $4, 'pending', $5)",
        feedback_id, skill_id, team_id, feedback_text, created_at,
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
):
    team = await _require_team_token(x_team_token)
    db = get_db()
    # Verify skill exists
    row = await db.fetchrow("SELECT id FROM skills WHERE id = $1", skill_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Skill not found")
    result = await submit_feedback(db, skill_id, body.feedback_text, team_id=team["id"])
    return result


@router.get("/feedback", dependencies=[Depends(require_user)])
async def get_feedback(status: Optional[str] = Query(None)):
    db = get_db()
    if status:
        rows = await db.fetch(
            "SELECT id, skill_id, team_id, feedback_text, status, created_at "
            "FROM skill_feedback WHERE status = $1 ORDER BY created_at DESC",
            status,
        )
    else:
        rows = await db.fetch(
            "SELECT id, skill_id, team_id, feedback_text, status, created_at "
            "FROM skill_feedback ORDER BY created_at DESC"
        )
    return {
        "feedback": [
            {
                "id": r["id"],
                "skill_id": r["skill_id"],
                "team_id": r["team_id"],
                "feedback_text": r["feedback_text"],
                "status": r["status"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]
    }


@router.patch("/feedback/{feedback_id}", dependencies=[Depends(require_user)])
async def update_feedback_status(feedback_id: str, body: StatusBody):
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
    r = await db.fetchrow(
        "SELECT id, skill_id, team_id, feedback_text, status, created_at "
        "FROM skill_feedback WHERE id = $1",
        feedback_id,
    )
    return {
        "id": r["id"],
        "skill_id": r["skill_id"],
        "team_id": r["team_id"],
        "feedback_text": r["feedback_text"],
        "status": r["status"],
        "created_at": r["created_at"],
    }
