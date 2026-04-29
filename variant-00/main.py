import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from src.middleware.rate_limit import limiter, rate_limit_exceeded_handler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("locker")
from vault.db import init_db, close_db
from src.auth.oauth import router as auth_router
from vault.routes import router as vault_router
from vault.team_routes import router as team_router
from vault.employee_routes import router as employee_router
from vault.usage import router as usage_router
from vault.feedback import router as feedback_router
from vault.org_routes import router as org_router
from vault.share_routes import router as share_router
from vault.invite_routes import router as invite_router
from vault.audit import router as audit_router
from proxy.routes import router as proxy_router
from locker_mcp.routes import router as mcp_router
from locker_mcp.sse_server import mcp_routes, mcp_v2
from locker_mcp.consent import router as consent_router
from fastapi.middleware.cors import CORSMiddleware



@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())[:8]
        # Identify caller: team token prefix or user ID
        team_token = request.headers.get("x-team-token", "")
        caller = f"team:{team_token[:8]}" if team_token else "anon"
        start = time.monotonic()
        try:
            response = await call_next(request)
            elapsed_ms = int((time.monotonic() - start) * 1000)
            response.headers["X-Request-ID"] = request_id
            logger.info(
                "req=%s %s %s caller=%s status=%d %dms",
                request_id, request.method, request.url.path, caller, response.status_code, elapsed_ms,
            )
            return response
        except Exception:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            logger.exception("req=%s %s %s caller=%s error %dms", request_id, request.method, request.url.path, caller, elapsed_ms)
            raise


app = FastAPI(title="Locker", lifespan=lifespan, routes=mcp_routes)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(SlowAPIMiddleware)

# CORS for frontend on Vercel
_DEFAULT_ORIGINS = ["https://web-theta-one-34.vercel.app"]
_env_origins = [o.strip() for o in os.environ.get("LOCKER_CORS_ORIGINS", "").split(",") if o.strip()]
_cors_origins = list(set(_DEFAULT_ORIGINS + _env_origins))
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
@limiter.exempt
async def health():
    return {"status": "ok", "phase": 3}


# --- OAuth Protected Resource Metadata (RFC 9728 §3.1) ---
# Scoped to /mcp/v2 so legacy /mcp clients (X-Team-Token auth) don't discover OAuth metadata

_BASE_URL = os.environ.get("LOCKER_BASE_URL", "https://locker.up.railway.app")


@app.get("/.well-known/oauth-protected-resource/mcp/v2")
@limiter.exempt
async def oauth_protected_resource():
    return JSONResponse({
        "resource": f"{_BASE_URL}/mcp/v2",
        "authorization_servers": [f"{_BASE_URL}/mcp/v2"],
        "bearer_methods_supported": ["header"],
    })


app.include_router(auth_router)
app.include_router(vault_router)
app.include_router(team_router)
app.include_router(employee_router)
app.include_router(usage_router)
app.include_router(feedback_router)
app.include_router(audit_router)
app.include_router(org_router)
app.include_router(share_router)
app.include_router(invite_router)
app.include_router(proxy_router)
app.include_router(mcp_router)
app.include_router(consent_router)

# Mount OAuth-protected FastMCP at /mcp/v2
app.mount("/mcp/v2", mcp_v2.sse_app())
