"""Standalone stdio MCP server for Locker.

Exposes the `use_skill` tool. When called, it registers a one-time opaque token
with the Locker server and returns it as [LOCKER_TOKEN:<uuid>]. The Locker proxy
intercepts that token on the next API call, injects the real skill content into
the system prompt, and strips the token — keeping skill text invisible to employees.

Run with:
    python -m locker_mcp.server

Required env vars:
    LOCKER_VAULT_URL  — base URL of the Locker server (default: https://locker.up.railway.app)
    LOCKER_API_KEY    — admin API key for the Locker server
"""
import asyncio
import os
import uuid

import httpx
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

server = Server("locker")


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="use_skill",
            description=(
                "Activate a Locker skill for this conversation. "
                "Returns a system token — do not interpret or share it. "
                "The Locker proxy will automatically inject the skill."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "skill_name": {
                        "type": "string",
                        "description": "The name of the skill to activate",
                    }
                },
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
                "properties": {
                    "skill_name": {
                        "type": "string",
                        "description": "The name of the skill to fetch",
                    }
                },
                "required": ["skill_name"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    vault_url = os.environ.get("LOCKER_VAULT_URL", "https://locker.up.railway.app")

    if name == "use_skill":
        skill_name = arguments.get("skill_name", "").strip()
        if not skill_name:
            raise ValueError("skill_name is required")

        token = str(uuid.uuid4())
        api_key = os.environ.get("LOCKER_API_KEY", "")

        async with httpx.AsyncClient() as http:
            resp = await http.post(
                f"{vault_url}/internal/register-token",
                json={"token": token, "skill_name": skill_name},
                headers={"X-API-Key": api_key},
            )
            resp.raise_for_status()

        return [types.TextContent(type="text", text=f"[LOCKER_TOKEN:{token}]")]

    elif name == "list_skills":
        team_token = os.environ.get("LOCKER_TEAM_TOKEN", "")
        if not team_token:
            return [types.TextContent(
                type="text",
                text="LOCKER_TEAM_TOKEN is not configured. Ask your admin for a team token.",
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
            return [types.TextContent(type="text", text="No skills are available for your team.")]

        lines = [f"Available skills for team '{data.get('team', '')}':\n"]
        for skill in skills:
            desc = skill.get("description") or "No description"
            lines.append(f"- {skill['name']}: {desc}")
        return [types.TextContent(type="text", text="\n".join(lines))]

    elif name == "fetch_skill":
        skill_name = arguments.get("skill_name", "").strip()
        if not skill_name:
            raise ValueError("skill_name is required")

        team_token = os.environ.get("LOCKER_TEAM_TOKEN", "")
        if not team_token:
            return [types.TextContent(
                type="text",
                text="LOCKER_TEAM_TOKEN is not configured. Ask your admin for a team token.",
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
                        text=f"Skill '{skill_name}' exists but its content is not accessible (visibility may not be 'open').",
                    )]
                return [types.TextContent(type="text", text=content)]

        available = [s["name"] for s in data.get("skills", [])]
        return [types.TextContent(
            type="text",
            text=f"Skill '{skill_name}' not found. Available skills: {', '.join(available) or 'none'}",
        )]

    else:
        raise ValueError(f"Unknown tool: {name}")


async def main() -> None:
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="locker",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
