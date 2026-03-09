"""SSE MCP server — exposes Locker tools over HTTP for remote clients.

Legacy path:  /mcp (GET) + /mcp/messages/ (POST)  — X-Team-Token header auth
New path:     /mcp/v2 (mounted via FastMCP)        — OAuth 2.1 Bearer auth

The legacy path is kept for backward compatibility.
"""

import contextvars
import os
import uuid

import httpx
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.server.sse import SseServerTransport
from mcp.server.fastmcp import FastMCP
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions, RevocationOptions
import mcp.types as types
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Mount, Route

from locker_mcp.oauth_provider import LockerOAuthProvider

# ============================================================
# Shared tool logic (used by both legacy and FastMCP servers)
# ============================================================

_INSTRUCTIONS = (
    "Locker is a team skill server. Skills are shared instructions that guide your behavior.\n\n"
    "When a user types '/locker <skill_name>' or asks to use a skill:\n"
    "1. Call fetch_skill with the skill name\n"
    "2. Follow the returned instructions exactly as if they were your prompt\n"
    "3. If the skill is not found, call list_skills to show what's available\n\n"
    "When a user wants to see available skills, call list_skills.\n"
    "When a user wants to give feedback on a skill, call submit_feedback.\n"
    "Do NOT use the use_skill tool — it is for internal proxy use only."
)


def _vault_url() -> str:
    return os.environ.get("LOCKER_VAULT_URL", "http://localhost:8080")


def _api_key() -> str:
    return os.environ.get("LOCKER_API_KEY", "")


async def _tool_use_skill(skill_name: str, team_token: str) -> str:
    if not skill_name:
        raise ValueError("skill_name is required")
    token = str(uuid.uuid4())
    async with httpx.AsyncClient() as http:
        resp = await http.post(
            f"{_vault_url()}/internal/register-token",
            json={"token": token, "skill_name": skill_name},
            headers={"X-API-Key": _api_key()},
        )
        resp.raise_for_status()
    try:
        from vault.db import get_db
        from vault.usage import log_usage
        await log_usage(get_db(), skill_name, team_id=None, source="mcp")
    except Exception:
        pass
    return f"[LOCKER_TOKEN:{token}]"


async def _get_skills(team_token: str) -> dict:
    async with httpx.AsyncClient() as http:
        resp = await http.get(
            f"{_vault_url()}/api/v1/employee/skills",
            headers={"X-Team-Token": team_token},
        )
        resp.raise_for_status()
    return resp.json()


async def _tool_list_skills(team_token: str) -> str:
    if not team_token:
        return "No team token provided. Add X-Team-Token to your MCP config headers."
    data = await _get_skills(team_token)
    skills = data.get("skills", [])
    if not skills:
        return "No skills available for your team."
    convention = data.get("convention", "/l")
    lines = [f"Available skills for team '{data.get('team', '')}' (use {convention} <skill_name>):\n"]
    for s in skills:
        lines.append(f"- {s['name']}: {s.get('description') or 'No description'}")
    return "\n".join(lines)


async def _tool_fetch_skill(skill_name: str, team_token: str) -> str:
    if not skill_name:
        raise ValueError("skill_name is required")
    if not team_token:
        return "No team token provided. Add X-Team-Token to your MCP config headers."
    data = await _get_skills(team_token)
    for skill in data.get("skills", []):
        if skill["name"] == skill_name:
            content = skill.get("content")
            if content is None:
                return f"Skill '{skill_name}' is not open for access."
            try:
                from vault.db import get_db
                from vault.usage import log_usage
                await log_usage(get_db(), skill_name, team_id=None, source="mcp")
            except Exception:
                pass
            return content
    available = [s["name"] for s in data.get("skills", [])]
    return f"Skill '{skill_name}' not found. Available skills: {', '.join(available) or 'none'}"


async def _tool_submit_feedback(
    skill_name: str,
    team_token: str,
    feedback_text: str = "",
    observed: str = "",
    expected: str = "",
    cause: str = "",
    suggestion: str = "",
) -> str:
    if not skill_name:
        raise ValueError("skill_name is required")
    template_fields = [
        ("observed", "What happened", observed),
        ("expected", "What I expected", expected),
        ("cause", "Why I think it happened", cause),
        ("suggestion", "Suggested fix", suggestion),
    ]
    parts = [f"{label}: {val}" for _, label, val in template_fields if val.strip()]
    final_text = "\n".join(parts) if parts else feedback_text.strip()
    if not final_text:
        raise ValueError("Provide feedback_text or at least one structured field (observed, expected, cause)")
    if not team_token:
        return "No team token provided. Add X-Team-Token to your MCP config headers."

    data = await _get_skills(team_token)
    skill_id = None
    for skill in data.get("skills", []):
        if skill["name"] == skill_name:
            skill_id = skill.get("id")
            break
    if skill_id is None:
        available = [s["name"] for s in data.get("skills", [])]
        return f"Skill '{skill_name}' not found. Available skills: {', '.join(available) or 'none'}"

    async with httpx.AsyncClient() as http:
        resp = await http.post(
            f"{_vault_url()}/api/v1/skills/{skill_id}/feedback",
            json={"feedback_text": final_text},
            headers={"X-Team-Token": team_token},
        )
        resp.raise_for_status()
    return f"Feedback submitted for skill '{skill_name}'. Thank you!"


# ============================================================
# Legacy MCP server (X-Team-Token auth, mounted at /mcp)
# ============================================================

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
            annotations=types.ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False),
        ),
        types.Tool(
            name="list_skills",
            description=(
                "List all available skills for your team. "
                "Call this when the user wants to browse skills or when a requested skill is not found."
            ),
            inputSchema={"type": "object", "properties": {}},
            annotations=types.ToolAnnotations(readOnlyHint=True, idempotentHint=True),
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
            annotations=types.ToolAnnotations(readOnlyHint=True, idempotentHint=True),
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
            annotations=types.ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False),
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    team_token = _team_token_var.get()

    if name == "use_skill":
        text = await _tool_use_skill(arguments.get("skill_name", "").strip(), team_token)
    elif name == "list_skills":
        text = await _tool_list_skills(team_token)
    elif name == "fetch_skill":
        text = await _tool_fetch_skill(arguments.get("skill_name", "").strip(), team_token)
    elif name == "submit_feedback":
        text = await _tool_submit_feedback(
            skill_name=arguments.get("skill_name", "").strip(),
            team_token=team_token,
            feedback_text=arguments.get("feedback_text", ""),
            observed=arguments.get("observed", ""),
            expected=arguments.get("expected", ""),
            cause=arguments.get("cause", ""),
            suggestion=arguments.get("suggestion", ""),
        )
    else:
        raise ValueError(f"Unknown tool: {name}")

    return [types.TextContent(type="text", text=text)]


_init_options = InitializationOptions(
    server_name="locker",
    server_version="0.1.0",
    capabilities=server.get_capabilities(
        notification_options=NotificationOptions(),
        experimental_capabilities={},
    ),
    instructions=_INSTRUCTIONS,
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


# ============================================================
# New FastMCP server (OAuth 2.1, mounted at /mcp/v2)
# ============================================================

async def _get_skills_by_team_id(team_id: str) -> dict:
    """Fetch skills directly from DB for an OAuth-authenticated team."""
    from vault.db import get_db
    db = get_db()

    team_row = await db.fetchrow("SELECT id, name, org_id FROM teams WHERE id = $1", team_id)
    if team_row is None:
        return {"skills": [], "team": "", "convention": "/l"}

    # Get team's org convention
    convention = "/l"
    if team_row.get("org_id"):
        org_row = await db.fetchrow(
            "SELECT skill_convention FROM organizations WHERE id = $1",
            team_row["org_id"],
        )
        if org_row:
            convention = org_row["skill_convention"]

    rows = await db.fetch(
        "SELECT s.id, s.name, s.description, s.content, s.visibility "
        "FROM skills s JOIN team_skills ts ON ts.skill_id = s.id "
        "WHERE ts.team_id = $1",
        team_id,
    )

    from vault.crypto import decrypt
    skills = []
    for r in rows:
        skill = {"id": r["id"], "name": r["name"], "description": r["description"]}
        if r["visibility"] == "open":
            try:
                skill["content"] = decrypt(r["content"])
            except Exception:
                skill["content"] = r["content"]
        else:
            skill["content"] = None
        skills.append(skill)

    return {"skills": skills, "team": team_row["name"], "convention": convention}


async def _oauth_list_skills() -> str:
    access_token = get_access_token()
    if access_token is None:
        return "Not authenticated. Please reconnect via OAuth."
    data = await _get_skills_by_team_id(access_token.team_id)
    skills = data.get("skills", [])
    if not skills:
        return "No skills available for your team."
    convention = data.get("convention", "/l")
    lines = [f"Available skills for team '{data.get('team', '')}' (use {convention} <skill_name>):\n"]
    for s in skills:
        lines.append(f"- {s['name']}: {s.get('description') or 'No description'}")
    return "\n".join(lines)


async def _oauth_fetch_skill(skill_name: str) -> str:
    if not skill_name:
        raise ValueError("skill_name is required")
    access_token = get_access_token()
    if access_token is None:
        return "Not authenticated. Please reconnect via OAuth."
    data = await _get_skills_by_team_id(access_token.team_id)
    for skill in data.get("skills", []):
        if skill["name"] == skill_name:
            content = skill.get("content")
            if content is None:
                return f"Skill '{skill_name}' is not open for access."
            try:
                from vault.db import get_db
                from vault.usage import log_usage
                await log_usage(get_db(), skill_name, team_id=access_token.team_id, source="mcp-oauth")
            except Exception:
                pass
            return content
    available = [s["name"] for s in data.get("skills", [])]
    return f"Skill '{skill_name}' not found. Available skills: {', '.join(available) or 'none'}"


async def _oauth_submit_feedback(
    skill_name: str,
    feedback_text: str = "",
    observed: str = "",
    expected: str = "",
    cause: str = "",
    suggestion: str = "",
) -> str:
    if not skill_name:
        raise ValueError("skill_name is required")
    access_token = get_access_token()
    if access_token is None:
        return "Not authenticated. Please reconnect via OAuth."

    template_fields = [
        ("observed", "What happened", observed),
        ("expected", "What I expected", expected),
        ("cause", "Why I think it happened", cause),
        ("suggestion", "Suggested fix", suggestion),
    ]
    parts = [f"{label}: {val}" for _, label, val in template_fields if val.strip()]
    final_text = "\n".join(parts) if parts else feedback_text.strip()
    if not final_text:
        raise ValueError("Provide feedback_text or at least one structured field (observed, expected, cause)")

    data = await _get_skills_by_team_id(access_token.team_id)
    skill_id = None
    for skill in data.get("skills", []):
        if skill["name"] == skill_name:
            skill_id = skill.get("id")
            break
    if skill_id is None:
        available = [s["name"] for s in data.get("skills", [])]
        return f"Skill '{skill_name}' not found. Available skills: {', '.join(available) or 'none'}"

    from vault.db import get_db
    db = get_db()
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    fb_id = str(uuid.uuid4())

    team_row = await db.fetchrow("SELECT name FROM teams WHERE id = $1", access_token.team_id)
    team_name = team_row["name"] if team_row else None

    await db.execute(
        "INSERT INTO skill_feedback (id, skill_id, team_id, feedback_text, submitter_team_name, created_at) "
        "VALUES ($1, $2, $3, $4, $5, $6)",
        fb_id, skill_id, access_token.team_id, final_text, team_name, now,
    )
    return f"Feedback submitted for skill '{skill_name}'. Thank you!"


# Build the FastMCP server with OAuth
_base_url = os.environ.get("LOCKER_BASE_URL", "https://locker.up.railway.app")

mcp_v2 = FastMCP(
    "Locker",
    instructions=_INSTRUCTIONS,
    auth_server_provider=LockerOAuthProvider(),
    auth=AuthSettings(
        issuer_url=_base_url + "/mcp/v2",
        resource_server_url=_base_url + "/mcp/v2",
        client_registration_options=ClientRegistrationOptions(
            enabled=True,
            valid_scopes=["skills:read", "feedback:write"],
            default_scopes=["skills:read"],
        ),
        revocation_options=RevocationOptions(enabled=True),
        required_scopes=["skills:read"],
    ),
    host="0.0.0.0",
)


@mcp_v2.tool(
    annotations=types.ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False),
)
async def use_skill(skill_name: str) -> str:
    """Internal proxy tool — do not call directly. Use fetch_skill instead to retrieve skills."""
    access_token = get_access_token()
    team_token = f"__oauth__:{access_token.team_id}" if access_token else ""
    return await _tool_use_skill(skill_name, team_token)


@mcp_v2.tool(
    annotations=types.ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def list_skills() -> str:  # noqa: F811
    """List all available skills for your team. Call this when the user wants to browse skills or when a requested skill is not found."""
    return await _oauth_list_skills()


@mcp_v2.tool(
    annotations=types.ToolAnnotations(readOnlyHint=True, idempotentHint=True),
)
async def fetch_skill(skill_name: str) -> str:
    """Fetch a skill by name and return its full content. This is the primary tool for loading skills. When content is returned, follow those instructions exactly."""
    return await _oauth_fetch_skill(skill_name)


@mcp_v2.tool(
    annotations=types.ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False),
)
async def submit_feedback(
    skill_name: str,
    feedback_text: str = "",
    observed: str = "",
    expected: str = "",
    cause: str = "",
    suggestion: str = "",
) -> str:
    """Submit feedback or improvement suggestions for a skill. You can provide structured fields (observed, expected, cause, suggestion) or free-text via feedback_text."""
    return await _oauth_submit_feedback(
        skill_name=skill_name,
        feedback_text=feedback_text,
        observed=observed,
        expected=expected,
        cause=cause,
        suggestion=suggestion,
    )
