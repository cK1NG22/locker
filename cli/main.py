from pathlib import Path
from typing import Optional

import typer

from cli.deploy import deploy as _deploy
from cli.deploy import deploy_folder as _deploy_folder
from cli.sync import sync as _sync

app = typer.Typer()


@app.command()
def deploy(
    skill_path: Path = typer.Argument(..., help="Path to skill file or references folder"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Skill description visible to employees"),
) -> None:
    if skill_path.is_dir():
        _deploy_folder(skill_path, description=description)
    else:
        _deploy(skill_path, description=description)


@app.command()
def sync(
    output_dir: Optional[Path] = typer.Option(None, "--output-dir", "-o", help="Directory to write skill files (default: ~/.claude/commands/)"),
) -> None:
    _sync(output_dir=output_dir)
