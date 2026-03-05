from pathlib import Path
from typing import Optional

import typer

from cli.deploy import deploy as _deploy
from cli.deploy import deploy_folder as _deploy_folder
from cli.setup import setup as _setup
from cli.sync import sync as _sync

app = typer.Typer()


@app.command()
def deploy(
    skill_path: Path = typer.Argument(..., help="Path to skill file or references folder"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Skill description visible to employees"),
    visibility: Optional[str] = typer.Option(None, "--visibility", "-v", help="Skill visibility: hidden, shared, or open (default: open)"),
) -> None:
    if visibility is not None and visibility not in ("hidden", "shared", "open"):
        typer.echo(f"Error: Invalid visibility '{visibility}'. Must be hidden, shared, or open.")
        raise typer.Exit(code=1)
    if skill_path.is_dir():
        _deploy_folder(skill_path, description=description, visibility=visibility)
    else:
        _deploy(skill_path, description=description, visibility=visibility)


@app.command()
def setup(
    url: Optional[str] = typer.Option(None, "--url", "-u", help="Locker server URL (default: https://locker.up.railway.app)"),
    team_token: Optional[str] = typer.Option(None, "--token", "-t", help="Your team token"),
) -> None:
    _setup(url=url, team_token=team_token)


@app.command()
def sync(
    output_dir: Optional[Path] = typer.Option(None, "--output-dir", "-o", help="Directory to write skill files (default: ~/.claude/commands/)"),
) -> None:
    _sync(output_dir=output_dir)
