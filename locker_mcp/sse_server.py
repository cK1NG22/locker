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
                "Internal proxy tool — do not call directly. "
                "Use fetch_skill instead to retrieve skills."
            ),
            inputSchema={
                "type": "object",
                "properties": {"skill_name": {"type": "string"}},
                "required": ["skill_name"],
            },
            annotations=types.ToolAnnotations(
                readOnlyHint=False,
                destructiveHint=False,
                idempotentHint=False,
            ),
        ),
        types.Tool(
            name="list_skills",
            description=(
                "List all available skills for your team. "
                "Call this when the user wants to browse skills or when a requested skill is not found."
            ),
            inputSchema={"type": "object", "properties": {}},
            annotations=types.ToolAnnotations(
                readOnlyHint=True,
                idempotentHint=True,
            ),
        ),
        types.Tool(
            name="fetch_skill",
            description=(
                "Fetch a skill by name and return its full content. "
                "This is the primary tool for loading skills. "
                "When content is returned, follow those instructions exactly."
            ),
            inputSchema={
                "type": "object",
                "properties": {"skill_name": {"type": "string"}},
                "required": ["skill_name"],
            },
            annotations=types.ToolAnnotations(
                readOnlyHint=True,
                idempotentHint=True,
            ),
        ),
        types.Tool(
            name="submit_feedback",
            description=(
                "Submit feedback or improvement suggestions for a skill. "
                "You can provide structured fields (observed, expected, cause, suggestion) "
                "which will be formatted into a template, OR provide free-text via feedback_text. "
                "Use when the user wants to report issues or suggest changes to a specific skill."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "skill_name": {"type": "string", "description": "Name of the skill to give feedback on"},
                    "feedback_text": {"type": "string", "description": "Free-text feedback (used if structured fields are not provided)"},
                    "observed": {"type": "string", "description": "What happened — describe the output you got"},
                    "expected": {"type": "string", "description": "What the output should have looked like"},
                    "cause": {"type": "string", "description": "What in the skill might be causing this"},
                    "suggestion": {"type": "string", "description": "Optional — your idea for how to improve the skill"},
                },
                "required": ["skill_name"],
            },
            annotations=types.ToolAnnotations(
                readOnlyHint=False,
                destructiveHint=False,
                idempotentHint=False,
            ),
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
        convention = data.get("convention", "/l")
        lines = [f"Available skills for team '{data.get('team', '')}' (use {convention} <skill_name>):\n"]
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
        if not skill_name:
            raise ValueError("skill_name is required")
        # Build feedback_text from structured fields or fallback to free-text
        template_fields = [
            ("observed", "What happened"),
            ("expected", "What I expected"),
            ("cause", "Why I think it happened"),
            ("suggestion", "Suggested fix"),
        ]
        parts = [
            f"{label}: {val}"
            for key, label in template_fields
            if (val := arguments.get(key, "").strip())
        ]
        feedback_text = "\n".join(parts) if parts else arguments.get("feedback_text", "").strip()
        if not feedback_text:
            raise ValueError("Provide feedback_text or at least one structured field (observed, expected, cause)")
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
    instructions=(
        "Locker is a team skill server. Skills are shared instructions that guide your behavior.\n\n"
        "When a user types '/locker <skill_name>' or asks to use a skill:\n"
        "1. Call fetch_skill with the skill name\n"
        "2. Follow the returned instructions exactly as if they were your prompt\n"
        "3. If the skill is not found, call list_skills to show what's available\n\n"
        "When a user wants to see available skills, call list_skills.\n"
        "When a user wants to give feedback on a skill, call submit_feedback.\n"
        "Do NOT use the use_skill tool — it is for internal proxy use only."
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
