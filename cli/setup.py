import json
import platform
from pathlib import Path
from typing import Optional

import httpx
import typer


CLAUDE_JSON_PATH = Path.home() / ".claude.json"
CLAUDE_DESKTOP_CONFIG_PATH = (
    Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    if platform.system() == "Darwin"
    else Path.home() / ".config" / "Claude" / "claude_desktop_config.json"
)
COMMANDS_DIR = Path.home() / ".claude" / "commands"
DEFAULT_URL = "https://locker.up.railway.app"
SKILL_RAW_URL = "https://raw.githubusercontent.com/ck22coding/locker-skill/main/locker.md"


def _write_claude_code_config(server_url: str, team_token: str) -> None:
    """Write Locker MCP entry to ~/.claude.json, preserving other config."""
    mcp_url = f"{server_url}/mcp"

    config: dict = {}
    if CLAUDE_JSON_PATH.exists():
        try:
            config = json.loads(CLAUDE_JSON_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            config = {}

    if "mcpServers" not in config:
        config["mcpServers"] = {}

    config["mcpServers"]["locker"] = {
        "type": "sse",
        "url": mcp_url,
        "headers": {
            "X-Team-Token": team_token,
        },
    }

    CLAUDE_JSON_PATH.write_text(json.dumps(config, indent=2) + "\n")
    typer.echo(f"  Claude Code config written to {CLAUDE_JSON_PATH}")


def _write_claude_desktop_config(server_url: str, team_token: str) -> None:
    """Write Locker MCP entry to Claude Desktop config, preserving other servers."""
    mcp_url = f"{server_url}/mcp"

    config: dict = {}
    if CLAUDE_DESKTOP_CONFIG_PATH.exists():
        try:
            config = json.loads(CLAUDE_DESKTOP_CONFIG_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            config = {}

    if "mcpServers" not in config:
        config["mcpServers"] = {}

    config["mcpServers"]["locker"] = {
        "type": "sse",
        "url": mcp_url,
        "headers": {
            "X-Team-Token": team_token,
        },
    }

    CLAUDE_DESKTOP_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CLAUDE_DESKTOP_CONFIG_PATH.write_text(json.dumps(config, indent=2) + "\n")
    typer.echo(f"  Claude Desktop config written to {CLAUDE_DESKTOP_CONFIG_PATH}")


def setup(
    url: Optional[str] = None,
    team_token: Optional[str] = None,
) -> None:
    """Write Locker MCP config to ~/.claude.json and install the /locker skill."""
    server_url = url or DEFAULT_URL

    if not team_token:
        team_token = typer.prompt("Enter your team token")

    _write_claude_code_config(server_url, team_token)
    _install_skill()
    typer.echo("Restart Claude Code to connect.")


def join(
    invite_code: str,
    url: Optional[str] = None,
) -> None:
    """Join a team via invite code. Configures Claude Code + Claude Desktop."""
    server_url = url or DEFAULT_URL
    api_url = f"{server_url}/api/v1/invite/join-cli"

    try:
        resp = httpx.post(
            api_url,
            json={"invite_code": invite_code},
            timeout=10,
        )
    except httpx.HTTPError as e:
        typer.echo(f"Error: Could not reach server at {server_url} — {e}")
        raise typer.Exit(code=1)

    if resp.status_code != 200:
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        typer.echo(f"Error: {detail}")
        raise typer.Exit(code=1)

    data = resp.json()
    team_name = data["team_name"]
    team_token = data["team_token"]
    result_url = data["server_url"]
    skill_count = data.get("skill_count", 0)

    typer.echo(f'Joining team "{team_name}"...')

    _write_claude_code_config(result_url, team_token)
    _write_claude_desktop_config(result_url, team_token)
    _install_skill()

    typer.echo(f'\nYou\'re in! Team "{team_name}" ({skill_count} skills) is ready.')
    typer.echo("Restart Claude Code or Claude Desktop to connect.")


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
