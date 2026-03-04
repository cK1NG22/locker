import json
import os

import httpx
from fastapi import APIRouter, HTTPException, Request, Response

from proxy.injector import inject_skills
from proxy.filter import filter_response
from proxy.ref_handler import handle_ref_requests

router = APIRouter(prefix="/proxy")

_ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"


@router.post("/anthropic/v1/messages")
async def anthropic_proxy(request: Request):
    body = await request.json()

    # Inject skills (raises 422 if a named skill is missing)
    body, injected_contents, has_ref_files = await inject_skills(body)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")

    forward_headers = {"x-api-key": api_key, "content-type": "application/json"}
    anthropic_version = request.headers.get("anthropic-version")
    if anthropic_version:
        forward_headers["anthropic-version"] = anthropic_version

    async with httpx.AsyncClient() as client:
        resp = await client.post(_ANTHROPIC_API_URL, json=body, headers=forward_headers)

    content = resp.content
    media_type = resp.headers.get("content-type", "application/json")

    if resp.status_code == 200 and has_ref_files:
        # Check if the LLM wants to read reference files (tool-use loop)
        response_json = json.loads(resp.content)
        content = await handle_ref_requests(
            response_json, body, forward_headers, injected_contents
        )
    elif resp.status_code == 200 and injected_contents:
        # No ref files — just filter as before
        content = filter_response(resp.content, injected_contents)

    return Response(
        content=content,
        status_code=resp.status_code,
        media_type=media_type,
    )
