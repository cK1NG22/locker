import os
from typing import Optional
from fastapi import Header, HTTPException


async def require_api_key(x_api_key: Optional[str] = Header(None, alias="X-API-Key")) -> None:
    expected = os.environ.get("LOCKER_API_KEY")
    if not expected or not x_api_key or x_api_key != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")
