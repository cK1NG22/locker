"""Audit logging — tracks admin actions."""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query

from src.auth import require_user
from vault.db import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_user)])


async def audit(db, actor_id: str, action: str, resource_type: str,
                resource_id: Optional[str] = None, metadata: Optional[dict] = None) -> None:
    """Insert an audit log row. Fire-and-forget; never raises."""
    try:
        await db.execute(
            "INSERT INTO audit_logs (id, actor_id, action, resource_type, resource_id, metadata, created_at) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7)",
            str(uuid.uuid4()),
            actor_id,
            action,
            resource_type,
            resource_id,
            json.dumps(metadata) if metadata else None,
            datetime.now(timezone.utc).isoformat(),
        )
    except Exception:
        logger.exception("Failed to write audit log")


@router.get("/audit-log")
async def get_audit_log(
    action: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    actor_id: Optional[str] = Query(None),
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    db = get_db()
    conditions = []
    params = []
    idx = 1

    if action:
        conditions.append(f"action = ${idx}")
        params.append(action)
        idx += 1
    if resource_type:
        conditions.append(f"resource_type = ${idx}")
        params.append(resource_type)
        idx += 1
    if actor_id:
        conditions.append(f"actor_id = ${idx}")
        params.append(actor_id)
        idx += 1
    if from_date:
        conditions.append(f"created_at >= ${idx}")
        params.append(from_date)
        idx += 1
    if to_date:
        conditions.append(f"created_at <= ${idx}")
        params.append(to_date)
        idx += 1

    where = (" WHERE " + " AND ".join(conditions)) if conditions else ""

    # Get total count
    count_row = await db.fetchrow(
        f"SELECT COUNT(*) AS total FROM audit_logs{where}", *params
    )
    total = count_row["total"]

    # Get paginated results
    rows = await db.fetch(
        f"SELECT id, actor_id, action, resource_type, resource_id, metadata, created_at "
        f"FROM audit_logs{where} ORDER BY created_at DESC "
        f"LIMIT ${idx} OFFSET ${idx + 1}",
        *params, limit, offset,
    )

    return {
        "logs": [
            {
                "id": r["id"],
                "actor_id": r["actor_id"],
                "action": r["action"],
                "resource_type": r["resource_type"],
                "resource_id": r["resource_id"],
                "metadata": json.loads(r["metadata"]) if r["metadata"] else None,
                "created_at": r["created_at"],
            }
            for r in rows
        ],
        "total": total,
    }
