import os
import uuid
from datetime import datetime, timezone, timedelta
import jwt

_SECRET_KEY = lambda: os.environ.get("LOCKER_JWT_SECRET", "dev-secret-change-me")
_ALGORITHM = "HS256"
_EXPIRY_HOURS = 24


def create_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=_EXPIRY_HOURS),
    }
    return jwt.encode(payload, _SECRET_KEY(), algorithm=_ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, _SECRET_KEY(), algorithms=[_ALGORITHM])
