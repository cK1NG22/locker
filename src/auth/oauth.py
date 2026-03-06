import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from src.middleware.rate_limit import limiter
from vault.db import get_db
from src.auth.jwt import create_token

router = APIRouter(prefix="/api/v1/auth")


class GoogleTokenRequest(BaseModel):
    token: str


@router.post("/google")
@limiter.limit("10/minute")
async def google_login(request: Request, body: GoogleTokenRequest):
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    if not client_id:
        raise HTTPException(status_code=500, detail="GOOGLE_CLIENT_ID not configured")

    try:
        idinfo = id_token.verify_oauth2_token(
            body.token, google_requests.Request(), client_id
        )
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Invalid Google token: {e}")

    google_id = idinfo["sub"]
    email = idinfo["email"]
    name = idinfo.get("name", "")

    db = get_db()
    now = datetime.now(timezone.utc).isoformat()

    # Upsert user
    row = await db.fetchrow(
        "SELECT id FROM users WHERE google_id = $1", google_id
    )

    if row:
        user_id = row["id"]
        await db.execute(
            "UPDATE users SET name = $1 WHERE id = $2", name, user_id
        )
    else:
        user_id = str(uuid.uuid4())
        await db.execute(
            "INSERT INTO users (id, email, name, google_id, created_at) VALUES ($1, $2, $3, $4, $5)",
            user_id, email, name, google_id, now,
        )

    access_token = create_token(user_id, email)
    return {
        "access_token": access_token,
        "user": {"id": user_id, "email": email, "name": name},
    }
