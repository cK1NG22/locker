from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.auth import require_api_key
from locker_mcp.token_store import register

router = APIRouter(prefix="/internal")


class RegisterTokenRequest(BaseModel):
    token: str
    skill_name: str


@router.post("/register-token", dependencies=[Depends(require_api_key)])
async def register_token_route(body: RegisterTokenRequest):
    register(body.token, body.skill_name)
    return {"ok": True}
