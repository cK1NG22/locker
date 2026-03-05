import json
import os
from pathlib import Path
from typing import Optional

import httpx
import typer


CLAUDE_JSON_PATH = Path.home() / ".claude.json"
COMMANDS_DIR = Path.home() / ".claude" / "commands"
DEFAULT_URL = "https://locker.up.railway.app"
SKILL_RAW_URL = "https://raw.githubusercontent.com/ck22coding/locker-skill/main/locker.md"


def setup(
    url: Optional[str] = None,
    team_token: Optional[str] = None,
) -> None:
    """Write Locker MCP config to ~/.claude.json and install the /locker skill."""
    server_url = url or DEFAULT_URL

    if not team_token:
        team_token = typer.prompt("Enter your team token")

    mcp_url = f"{server_url}/mcp"

    # Read or create ~/.claude.json
    config: dict = {}
    if CLAUDE_JSON_PATH.exists():
        try:
            config = json.loads(CLAUDE_JSON_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            config = {}

    # Ensure mcpServers key exists
    if "mcpServers" not in config:
        config["mcpServers"] = {}

    # Add/update the locker entry
    config["mcpServers"]["locker"] = {
        "type": "sse",
        "url": mcp_url,
        "headers": {
            "X-Team-Token": team_token,
        },
    }

    # Write back
    CLAUDE_JSON_PATH.write_text(json.dumps(config, indent=2) + "\n")
    typer.echo(f"MCP config written to {CLAUDE_JSON_PATH}")
    typer.echo(f"  Server: {mcp_url}")

    # Download /locker skill router
    _install_skill()

    typer.echo("Restart Claude Code to connect.")


def _install_skill() -> None:
    """Download locker.md skill router to ~/.claude/commands/."""
    dest = COMMANDS_DIR / "locker.md"
    if dest.exists():
        overwrite = typer.confirm(f"{dest} already exists. Overwrite?", default=True)
        if not overwrite:
            typer.echo("  Skipped skill install.")
            return

    try:
        resp = httpx.get(SKILL_RAW_URL, follow_redirects=True, timeout=10)
        resp.raise_for_status()
    except httpx.HTTPError as e:
        typer.echo(f"  Warning: Could not download skill router: {e}")
        return

    COMMANDS_DIR.mkdir(parents=True, exist_ok=True)
    dest.write_text(resp.text)
    typer.echo(f"  Skill router installed to {dest}")
