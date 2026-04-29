"""Auth dependency that accepts X-API-Key or Bearer JWT (per interface-contract)."""

import hmac
import os
from typing import Optional

from fastapi import Header

from src.auth import require_user as _require_jwt


async def require_user(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
) -> dict:
    """Accept X-API-Key or Bearer JWT for admin routes."""
    api_key = os.environ.get("LOCKER_API_KEY")
    if api_key and x_api_key and hmac.compare_digest(x_api_key, api_key):
        return {"sub": "api-key", "email": "api-key@locker.local"}
    return await _require_jwt(authorization=authorization)
