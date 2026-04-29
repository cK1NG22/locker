import os
from pathlib import Path
from typing import Optional

import httpx
import typer


def sync(output_dir: Optional[Path] = None) -> None:
    vault_url = os.environ.get("LOCKER_VAULT_URL")
    if not vault_url:
        typer.echo("Error: LOCKER_VAULT_URL environment variable is not set.")
        raise typer.Exit(code=1)

    team_token = os.environ.get("LOCKER_TEAM_TOKEN")
    if not team_token:
        typer.echo("Error: LOCKER_TEAM_TOKEN environment variable is not set.")
        raise typer.Exit(code=1)

    if output_dir is None:
        output_dir = Path.home() / ".claude" / "commands"

    try:
        r = httpx.get(
            f"{vault_url}/api/v1/employee/skills",
            headers={"X-Team-Token": team_token},
        )
    except httpx.RequestError as e:
        typer.echo(f"Error: Request failed: {e}")
        raise typer.Exit(code=1)

    if r.status_code != 200:
        try:
            detail = r.json().get("detail", r.text)
        except Exception:
            detail = r.text
        typer.echo(f"Error: {r.status_code} {detail}")
        raise typer.Exit(code=1)

    data = r.json()
    skills = data.get("skills", [])

    output_dir.mkdir(parents=True, exist_ok=True)

    synced = []
    skipped = []
    for skill in skills:
        name = skill["name"]
        content = skill.get("content")
        if content is not None:
            (output_dir / f"{name}.md").write_text(content)
            synced.append(name)
        else:
            skipped.append(name)

    for name in synced:
        typer.echo(f"  + {name}")

    if skipped:
        typer.echo(f"  (skipped {len(skipped)} shared skill(s) — content not available: {', '.join(skipped)})")

    typer.echo(f"Synced {len(synced)} skill(s) to {output_dir}/")
