from fastapi import APIRouter, Depends
from pydantic import BaseModel

from vault.auth_deps import require_user
from locker_mcp.token_store import register

router = APIRouter(prefix="/internal")


class RegisterTokenRequest(BaseModel):
    token: str
    skill_name: str


@router.post("/register-token", dependencies=[Depends(require_user)])
async def register_token_route(body: RegisterTokenRequest):
    register(body.token, body.skill_name)
    return {"ok": True}
