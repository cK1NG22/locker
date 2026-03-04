from pathlib import Path
from typing import Optional

import typer

from cli.deploy import deploy as _deploy
from cli.deploy import deploy_folder as _deploy_folder

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
