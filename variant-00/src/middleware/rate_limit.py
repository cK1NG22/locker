"""Rate limiting via slowapi — per-IP, per-token, per-user buckets."""

import logging

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded

from src.auth.jwt import decode_token

logger = logging.getLogger(__name__)


def get_rate_limit_key(request: Request) -> str:
    """Return a rate-limit bucket key based on caller identity."""
    # Admin: JWT bearer token → use user ID (sub)
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        try:
            payload = decode_token(auth[7:])
            return f"user:{payload['sub']}"
        except Exception:
            pass

    # Employee: team token
    team_token = request.headers.get("X-Team-Token")
    if team_token:
        return f"team:{team_token}"

    # Public: client IP
    return f"ip:{request.client.host}" if request.client else "ip:unknown"


limiter = Limiter(key_func=get_rate_limit_key, default_limits=["120/minute"])


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    logger.warning("Rate limit exceeded: %s %s key=%s", request.method, request.url.path, get_rate_limit_key(request))
    retry_after = str(exc.detail).split(" ")[-1] if exc.detail else "60"
    # Extract just the numeric seconds if present
    try:
        int(retry_after)
    except ValueError:
        retry_after = "60"
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded"},
        headers={"Retry-After": retry_after},
    )
