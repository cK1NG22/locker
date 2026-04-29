"""SSE MCP server — exposes Locker tools over HTTP for remote clients.

Legacy path:  /mcp (GET) + /mcp/messages/ (POST)  — X-Team-Token header auth
New path:     /mcp/v2 (mounted via FastMCP)        — OAuth 2.1 Bearer auth

The legacy path is kept for backward compatibility.
"""

import contextvars
import os
import time
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
from starlette.responses import JSONResponse, Response
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


_NO_TOKEN_MSG = "No token provided. Add X-User-Token (personal) or X-Team-Token (team) to your MCP config headers."


def _vault_url() -> str:
    return os.environ.get("LOCKER_VAULT_URL", "http://localhost:8080")


def _api_key() -> str:
    return os.environ.get("LOCKER_API_KEY", "")


async def _tool_use_skill(skill_name: str, team_token: str) -> str:
    if not skill_name:
        raise ValueError("skill_name is required")
    token = str(uuid.uuid4())
    async with httpx.AsyncClient(timeout=10) as http:
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


def _format_feedback_text(
    feedback_text: str, observed: str, expected: str, cause: str, suggestion: str,
) -> str:
    """Build feedback text from structured fields, falling back to free-text."""
    template_fields = [
        ("What happened", observed),
        ("What I expected", expected),
        ("Why I think it happened", cause),
        ("Suggested fix", suggestion),
    ]
    parts = [f"{label}: {val}" for label, val in template_fields if val.strip()]
    text = "\n".join(parts) if parts else feedback_text.strip()
    if not text:
        raise ValueError("Provide feedback_text or at least one structured field (observed, expected, cause)")
    return text


def _find_skill(skills: list[dict], skill_name: str) -> dict | None:
    """Find a skill by name in a skills list."""
    return next((s for s in skills if s["name"] == skill_name), None)


def _skill_not_found_msg(skill_name: str, skills: list[dict]) -> str:
    available = [s["name"] for s in skills]
    return f"Skill '{skill_name}' not found. Available skills: {', '.join(available) or 'none'}"


def _auth_headers(team_token: str) -> dict:
    """Convert internal token representation to the appropriate HTTP header."""
    if team_token.startswith("__pat__:"):
        return {"X-User-Token": team_token[len("__pat__:"):]}
    return {"X-Team-Token": team_token}


async def _get_skills(team_token: str) -> dict:
    async with httpx.AsyncClient(timeout=10) as http:
        resp = await http.get(
            f"{_vault_url()}/api/v1/employee/skills",
            headers=_auth_headers(team_token),
        )
        resp.raise_for_status()
    return resp.json()


async def _tool_list_skills(team_token: str) -> str:
    if not team_token:
        return _NO_TOKEN_MSG
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
        return _NO_TOKEN_MSG
    data = await _get_skills(team_token)
    skills = data.get("skills", [])
    skill = _find_skill(skills, skill_name)
    if skill is None:
        return _skill_not_found_msg(skill_name, skills)
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
    final_text = _format_feedback_text(feedback_text, observed, expected, cause, suggestion)
    if not team_token:
        return _NO_TOKEN_MSG

    data = await _get_skills(team_token)
    skills = data.get("skills", [])
    skill = _find_skill(skills, skill_name)
    if skill is None:
        return _skill_not_found_msg(skill_name, skills)

    async with httpx.AsyncClient(timeout=10) as http:
        resp = await http.post(
            f"{_vault_url()}/api/v1/skills/{skill['id']}/feedback",
            json={"feedback_text": final_text},
            headers=_auth_headers(team_token),
        )
        resp.raise_for_status()
    return f"Feedback submitted for skill '{skill_name}'."


# ============================================================
# SSE connection rate limiter (per-IP, in-memory with TTL)
# ============================================================

_SSE_RATE_LIMIT = 20  # max connections per window
_SSE_RATE_WINDOW = 60  # seconds
_sse_connections: dict[str, list[float]] = {}


def _check_sse_rate_limit(client_ip: str) -> bool:
    """Return True if the connection is allowed, False if rate-limited."""
    now = time.monotonic()
    timestamps = _sse_connections.get(client_ip, [])
    # Prune expired entries for this IP
    timestamps = [t for t in timestamps if now - t < _SSE_RATE_WINDOW]
    if len(timestamps) >= _SSE_RATE_LIMIT:
        _sse_connections[client_ip] = timestamps
        return False
    timestamps.append(now)
    _sse_connections[client_ip] = timestamps
    return True


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
    # Rate limit SSE connections per IP
    client_ip = request.client.host if request.client else "unknown"
    if not _check_sse_rate_limit(client_ip):
        return JSONResponse({"detail": "Rate limit exceeded"}, status_code=429)

    # Prefer X-User-Token (PAT) over X-Team-Token for auth
    user_token = request.headers.get("x-user-token", "")
    team_token = request.headers.get("x-team-token", "")
    effective_token = f"__pat__:{user_token}" if user_token else team_token
    token = _team_token_var.set(effective_token)
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
    skills = data.get("skills", [])
    skill = _find_skill(skills, skill_name)
    if skill is None:
        return _skill_not_found_msg(skill_name, skills)
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

    final_text = _format_feedback_text(feedback_text, observed, expected, cause, suggestion)

    data = await _get_skills_by_team_id(access_token.team_id)
    skills = data.get("skills", [])
    skill = _find_skill(skills, skill_name)
    if skill is None:
        return _skill_not_found_msg(skill_name, skills)

    from vault.db import get_db
    from vault.feedback import submit_feedback
    db = get_db()
    team_row = await db.fetchrow("SELECT name FROM teams WHERE id = $1", access_token.team_id)
    await submit_feedback(
        db, skill["id"], final_text,
        team_id=access_token.team_id,
        submitter_team_name=team_row["name"] if team_row else None,
    )
    return f"Feedback submitted for skill '{skill_name}'."


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
