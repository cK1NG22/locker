import os
import re
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from src.middleware.rate_limit import limiter, rate_limit_exceeded_handler
from vault.db import init_db, close_db
from src.auth.oauth import router as auth_router
from vault.routes import router as vault_router
from vault.team_routes import router as team_router
from vault.employee_routes import router as employee_router
from vault.usage import router as usage_router
from vault.feedback import router as feedback_router
from vault.org_routes import router as org_router
from vault.share_routes import router as share_router
from vault.audit import router as audit_router
from proxy.routes import router as proxy_router
from locker_mcp.routes import router as mcp_router
from locker_mcp.sse_server import mcp_routes, mcp_v2
from locker_mcp.consent import router as consent_router



@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()


app = FastAPI(title="Locker", lifespan=lifespan, routes=mcp_routes)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


@app.get("/health")
@limiter.exempt
async def health():
    return {"status": "ok", "phase": 3}


# --- OAuth Protected Resource Metadata (RFC 9728) ---

_BASE_URL = os.environ.get("LOCKER_BASE_URL", "https://locker.up.railway.app")


@app.get("/.well-known/oauth-protected-resource")
@limiter.exempt
async def oauth_protected_resource():
    return JSONResponse({
        "resource": f"{_BASE_URL}/mcp/v2",
        "authorization_servers": [f"{_BASE_URL}/mcp/v2"],
        "bearer_methods_supported": ["header"],
    })


UUID_RE = re.compile(r'^[0-9a-f\-]{36}$')

@app.get("/setup/{team_token}", response_class=PlainTextResponse)
@limiter.exempt
async def setup_script(team_token: str, request: Request):
    if not UUID_RE.match(team_token):
        return PlainTextResponse("Invalid token format.", status_code=400)
    server_url = str(request.base_url).rstrip("/")
    skill_router_url = "https://raw.githubusercontent.com/ck22coding/locker-skill/main/locker.md"
    script = f"""#!/bin/bash
set -e
echo "Setting up Locker..."
python3 - <<'PYEOF'
import json, pathlib
p = pathlib.Path.home() / '.claude.json'
cfg = json.loads(p.read_text()) if p.exists() else {{}}
cfg.setdefault('mcpServers', {{}})['locker'] = {{
    'type': 'sse',
    'url': '{server_url}/mcp',
    'headers': {{'X-Team-Token': '{team_token}'}}
}}
p.write_text(json.dumps(cfg, indent=2))
print("MCP config written.")
PYEOF
mkdir -p ~/.claude/commands
curl -fsSL {skill_router_url} -o ~/.claude/commands/locker.md
echo "Skill router installed."
echo ""
echo "Done! Restart Claude Code, then try: /locker code-review"
"""
    return PlainTextResponse(script, media_type="text/plain")


app.include_router(auth_router)
app.include_router(vault_router)
app.include_router(team_router)
app.include_router(employee_router)
app.include_router(usage_router)
app.include_router(feedback_router)
app.include_router(audit_router)
app.include_router(org_router)
app.include_router(share_router)
app.include_router(proxy_router)
app.include_router(mcp_router)
app.include_router(consent_router)

# Mount OAuth-protected FastMCP at /mcp/v2
app.mount("/mcp/v2", mcp_v2.sse_app())

# Serve companion page static files if the build output exists
_companion_dir = Path(os.environ.get("LOCKER_STATIC_DIR", "./static/companion"))
if _companion_dir.is_dir():
    app.mount("/companion", StaticFiles(directory=str(_companion_dir), html=True), name="companion")

# Serve admin dashboard static files if the build output exists
_dashboard_dir = Path(os.environ.get("LOCKER_DASHBOARD_DIR", "./static/dashboard"))
if _dashboard_dir.is_dir():
    app.mount("/dashboard", StaticFiles(directory=str(_dashboard_dir), html=True), name="dashboard")
