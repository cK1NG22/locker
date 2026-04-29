import os
from pathlib import Path
from typing import Optional, Tuple

import httpx
import typer


def _get_credentials() -> Tuple[str, dict]:
    vault_url = os.environ.get("LOCKER_VAULT_URL")
    if not vault_url:
        typer.echo("Error: LOCKER_VAULT_URL environment variable is not set.")
        raise typer.Exit(code=1)

    api_key = os.environ.get("LOCKER_API_KEY")
    jwt_token = os.environ.get("LOCKER_JWT_TOKEN")
    if api_key:
        return vault_url, {"X-API-Key": api_key}
    if jwt_token:
        return vault_url, {"Authorization": f"Bearer {jwt_token}"}
    typer.echo("Error: Set LOCKER_API_KEY or LOCKER_JWT_TOKEN.")
    raise typer.Exit(code=1)


def deploy(file_path: Path, description: Optional[str] = None, visibility: Optional[str] = None) -> None:
    vault_url, headers = _get_credentials()

    if not file_path.exists():
        typer.echo(f"Error: File not found: {file_path}")
        raise typer.Exit(code=1)

    skill_name = file_path.stem
    content = file_path.read_text()

    payload: dict = {"name": skill_name, "content": content}
    if description is not None:
        payload["description"] = description
    if visibility is not None:
        payload["visibility"] = visibility

    try:
        r = httpx.post(
            f"{vault_url}/api/v1/skills",
            json=payload,
            headers=headers,
        )
    except httpx.RequestError as e:
        typer.echo(f"Error: Request failed: {e}")
        raise typer.Exit(code=1)

    if r.status_code in (200, 201):
        data = r.json()
        typer.echo(f'Deployed skill "{skill_name}" (id: {data["id"]})')
    else:
        try:
            detail = r.json().get("detail", r.text)
        except Exception:
            detail = r.text
        typer.echo(f"Error: {r.status_code} {detail}")
        raise typer.Exit(code=1)


def deploy_folder(folder_path: Path, description: Optional[str] = None, visibility: Optional[str] = None) -> None:
    vault_url, headers = _get_credentials()

    if not folder_path.exists():
        typer.echo(f"Error: Folder not found: {folder_path}")
        raise typer.Exit(code=1)

    stem = folder_path.name
    sibling_md = folder_path.parent / f"{stem}.md"

    if not sibling_md.exists():
        typer.echo(f"Error: Expected sibling file not found: {sibling_md}")
        raise typer.Exit(code=1)

    content = sibling_md.read_text()

    files = []
    for file in sorted(folder_path.rglob("*")):
        if file.is_file():
            rel = file.relative_to(folder_path)
            files.append({"path": str(rel), "content": file.read_text()})

    payload: dict = {"name": stem, "content": content, "files": files}
    if description is not None:
        payload["description"] = description
    if visibility is not None:
        payload["visibility"] = visibility

    try:
        r = httpx.post(
            f"{vault_url}/api/v1/skills/deploy-folder",
            json=payload,
            headers=headers,
        )
    except httpx.RequestError as e:
        typer.echo(f"Error: Request failed: {e}")
        raise typer.Exit(code=1)

    if r.status_code in (200, 201):
        data = r.json()
        typer.echo(
            f'Deployed skill "{stem}" (id: {data["id"]}) with {len(files)} reference file(s)'
        )
    else:
        try:
            detail = r.json().get("detail", r.text)
        except Exception:
            detail = r.text
        typer.echo(f"Error: {r.status_code} {detail}")
        raise typer.Exit(code=1)
