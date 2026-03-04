import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from vault.db import init_db, close_db
from vault.routes import router as vault_router
from vault.team_routes import router as team_router
from vault.employee_routes import router as employee_router
from proxy.routes import router as proxy_router
from locker_mcp.routes import router as mcp_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()


app = FastAPI(title="Locker", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok"}


app.include_router(vault_router)
app.include_router(team_router)
app.include_router(employee_router)
app.include_router(proxy_router)
app.include_router(mcp_router)

# Serve companion page static files if the build output exists
_companion_dir = Path(os.environ.get("LOCKER_STATIC_DIR", "./static/companion"))
if _companion_dir.is_dir():
    app.mount("/companion", StaticFiles(directory=str(_companion_dir), html=True), name="companion")

# Serve admin dashboard static files if the build output exists
_dashboard_dir = Path(os.environ.get("LOCKER_DASHBOARD_DIR", "./static/dashboard"))
if _dashboard_dir.is_dir():
    app.mount("/dashboard", StaticFiles(directory=str(_dashboard_dir), html=True), name="dashboard")
