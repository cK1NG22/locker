"""Feedback / refine system — lets team members submit feedback on skills."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel

from src.auth import require_api_key
from vault.db import get_db


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
    cursor = await db.execute(
        "SELECT id, name FROM teams WHERE token = ?", (x_team_token,)
    )
    row = await cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return {"id": row["id"], "name": row["name"]}


async def submit_feedback(db, skill_id: str, feedback_text: str, team_id: Optional[str] = None) -> dict:
    """Insert a feedback row and return it."""
    feedback_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    await db.execute(
        "INSERT INTO skill_feedback (id, skill_id, team_id, feedback_text, status, created_at) "
        "VALUES (?, ?, ?, ?, 'pending', ?)",
        (feedback_id, skill_id, team_id, feedback_text, created_at),
    )
    await db.commit()
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
async def post_feedback(
    skill_id: str,
    body: FeedbackBody,
    x_team_token: Optional[str] = Header(None, alias="X-Team-Token"),
):
    team = await _require_team_token(x_team_token)
    db = get_db()
    # Verify skill exists
    cursor = await db.execute("SELECT id FROM skills WHERE id = ?", (skill_id,))
    if await cursor.fetchone() is None:
        raise HTTPException(status_code=404, detail="Skill not found")
    result = await submit_feedback(db, skill_id, body.feedback_text, team_id=team["id"])
    return result


@router.get("/feedback", dependencies=[Depends(require_api_key)])
async def get_feedback(status: Optional[str] = Query(None)):
    db = get_db()
    if status:
        cursor = await db.execute(
            "SELECT id, skill_id, team_id, feedback_text, status, created_at "
            "FROM skill_feedback WHERE status = ? ORDER BY created_at DESC",
            (status,),
        )
    else:
        cursor = await db.execute(
            "SELECT id, skill_id, team_id, feedback_text, status, created_at "
            "FROM skill_feedback ORDER BY created_at DESC"
        )
    rows = await cursor.fetchall()
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


@router.patch("/feedback/{feedback_id}", dependencies=[Depends(require_api_key)])
async def update_feedback_status(feedback_id: str, body: StatusBody):
    if body.status not in ("reviewed", "applied"):
        raise HTTPException(status_code=400, detail="Status must be 'reviewed' or 'applied'")
    db = get_db()
    cursor = await db.execute(
        "SELECT id FROM skill_feedback WHERE id = ?", (feedback_id,)
    )
    if await cursor.fetchone() is None:
        raise HTTPException(status_code=404, detail="Feedback not found")
    await db.execute(
        "UPDATE skill_feedback SET status = ? WHERE id = ?",
        (body.status, feedback_id),
    )
    await db.commit()
    cursor = await db.execute(
        "SELECT id, skill_id, team_id, feedback_text, status, created_at "
        "FROM skill_feedback WHERE id = ?",
        (feedback_id,),
    )
    r = await cursor.fetchone()
    return {
        "id": r["id"],
        "skill_id": r["skill_id"],
        "team_id": r["team_id"],
        "feedback_text": r["feedback_text"],
        "status": r["status"],
        "created_at": r["created_at"],
    }
