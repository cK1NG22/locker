"""SSE MCP server — exposes Locker tools over HTTP for remote clients.

Mounted at /mcp (GET) and /mcp/messages/ (POST) in main.py.
Clients authenticate by passing X-Team-Token in their MCP config headers.
"""
import contextvars
import os
import uuid

import httpx
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.server.sse import SseServerTransport
import mcp.types as types
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Mount, Route

# Per-connection team token, set from request header before server.run()
_team_token_var: contextvars.ContextVar[str] = contextvars.ContextVar("team_token", default="")

sse_transport = SseServerTransport("/mcp/messages/")

server = Server("locker")


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="use_skill",
            description=(
                "Activate a Locker skill for this conversation. "
                "Returns a system token — do not interpret or share it."
            ),
            inputSchema={
                "type": "object",
                "properties": {"skill_name": {"type": "string"}},
                "required": ["skill_name"],
            },
        ),
        types.Tool(
            name="list_skills",
            description="List available Locker skills for your team.",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="fetch_skill",
            description=(
                "Fetch the full content of an open Locker skill by name. "
                "Returns the skill's instructions for you to follow directly."
            ),
            inputSchema={
                "type": "object",
                "properties": {"skill_name": {"type": "string"}},
                "required": ["skill_name"],
            },
        ),
        types.Tool(
            name="submit_feedback",
            description=(
                "Submit feedback on a Locker skill. "
                "Use this when the user wants to suggest improvements or report issues with a skill."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "skill_name": {"type": "string"},
                    "feedback_text": {"type": "string"},
                },
                "required": ["skill_name", "feedback_text"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    vault_url = os.environ.get("LOCKER_VAULT_URL", "http://localhost:8000")
    api_key = os.environ.get("LOCKER_API_KEY", "")
    team_token = _team_token_var.get()

    if name == "use_skill":
        skill_name = arguments.get("skill_name", "").strip()
        if not skill_name:
            raise ValueError("skill_name is required")
        token = str(uuid.uuid4())
        async with httpx.AsyncClient() as http:
            resp = await http.post(
                f"{vault_url}/internal/register-token",
                json={"token": token, "skill_name": skill_name},
                headers={"X-API-Key": api_key},
            )
            resp.raise_for_status()
        # Log usage (best-effort)
        try:
            from vault.db import get_db
            from vault.usage import log_usage
            await log_usage(get_db(), skill_name, team_id=None, source="mcp")
        except Exception:
            pass
        return [types.TextContent(type="text", text=f"[LOCKER_TOKEN:{token}]")]

    elif name == "list_skills":
        if not team_token:
            return [types.TextContent(
                type="text",
                text="No team token provided. Add X-Team-Token to your MCP config headers.",
            )]
        async with httpx.AsyncClient() as http:
            resp = await http.get(
                f"{vault_url}/api/v1/employee/skills",
                headers={"X-Team-Token": team_token},
            )
            resp.raise_for_status()
        data = resp.json()
        skills = data.get("skills", [])
        if not skills:
            return [types.TextContent(type="text", text="No skills available for your team.")]
        lines = [f"Available skills for team '{data.get('team', '')}':\n"]
        for s in skills:
            lines.append(f"- {s['name']}: {s.get('description') or 'No description'}")
        return [types.TextContent(type="text", text="\n".join(lines))]

    elif name == "fetch_skill":
        skill_name = arguments.get("skill_name", "").strip()
        if not skill_name:
            raise ValueError("skill_name is required")
        if not team_token:
            return [types.TextContent(
                type="text",
                text="No team token provided. Add X-Team-Token to your MCP config headers.",
            )]
        async with httpx.AsyncClient() as http:
            resp = await http.get(
                f"{vault_url}/api/v1/employee/skills",
                headers={"X-Team-Token": team_token},
            )
            resp.raise_for_status()
        data = resp.json()
        for skill in data.get("skills", []):
            if skill["name"] == skill_name:
                content = skill.get("content")
                if content is None:
                    return [types.TextContent(
                        type="text",
                        text=f"Skill '{skill_name}' is not open for access.",
                    )]
                # Log usage (best-effort)
                try:
                    from vault.db import get_db
                    from vault.usage import log_usage
                    await log_usage(get_db(), skill_name, team_id=None, source="mcp")
                except Exception:
                    pass
                return [types.TextContent(type="text", text=content)]
        available = [s["name"] for s in data.get("skills", [])]
        return [types.TextContent(
            type="text",
            text=f"Skill '{skill_name}' not found. Available skills: {', '.join(available) or 'none'}",
        )]

    elif name == "submit_feedback":
        skill_name = arguments.get("skill_name", "").strip()
        feedback_text = arguments.get("feedback_text", "").strip()
        if not skill_name:
            raise ValueError("skill_name is required")
        if not feedback_text:
            raise ValueError("feedback_text is required")
        if not team_token:
            return [types.TextContent(
                type="text",
                text="No team token provided. Add X-Team-Token to your MCP config headers.",
            )]
        # Look up skill ID from employee endpoint
        async with httpx.AsyncClient() as http:
            resp = await http.get(
                f"{vault_url}/api/v1/employee/skills",
                headers={"X-Team-Token": team_token},
            )
            resp.raise_for_status()
        data = resp.json()
        skill_id = None
        for skill in data.get("skills", []):
            if skill["name"] == skill_name:
                skill_id = skill.get("id")
                break
        if skill_id is None:
            available = [s["name"] for s in data.get("skills", [])]
            return [types.TextContent(
                type="text",
                text=f"Skill '{skill_name}' not found. Available skills: {', '.join(available) or 'none'}",
            )]
        # Submit feedback via API
        async with httpx.AsyncClient() as http:
            resp = await http.post(
                f"{vault_url}/api/v1/skills/{skill_id}/feedback",
                json={"feedback_text": feedback_text},
                headers={"X-Team-Token": team_token},
            )
            resp.raise_for_status()
        return [types.TextContent(
            type="text",
            text=f"Feedback submitted for skill '{skill_name}'. Thank you!",
        )]

    raise ValueError(f"Unknown tool: {name}")


_init_options = InitializationOptions(
    server_name="locker",
    server_version="0.1.0",
    capabilities=server.get_capabilities(
        notification_options=NotificationOptions(),
        experimental_capabilities={},
    ),
)


async def handle_sse(request: Request) -> Response:
    team_token = request.headers.get("x-team-token", "")
    token = _team_token_var.set(team_token)
    try:
        async with sse_transport.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            await server.run(streams[0], streams[1], _init_options)
    finally:
        _team_token_var.reset(token)
    return Response()


mcp_routes = [
    Route("/mcp", endpoint=handle_sse, methods=["GET"]),
    Mount("/mcp/messages/", app=sse_transport.handle_post_message),
]
