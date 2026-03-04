import httpx
import pytest
import respx
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()

VAULT_URL = "http://localhost:8000"
API_KEY = "test-key"
SKILL_RESPONSE = {"id": "abc123", "name": "email-style", "created_at": "2024-01-01"}


def test_successful_deploy(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCKER_VAULT_URL", VAULT_URL)
    monkeypatch.setenv("LOCKER_API_KEY", API_KEY)

    skill_file = tmp_path / "email-style.txt"
    skill_file.write_text("Always write concise emails.")

    with respx.mock:
        respx.post(f"{VAULT_URL}/api/v1/skills").mock(
            return_value=httpx.Response(201, json=SKILL_RESPONSE)
        )
        result = runner.invoke(app, [str(skill_file)])

    assert result.exit_code == 0
    assert 'Deployed skill "email-style" (id: abc123)' in result.output


def test_file_not_found(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCKER_VAULT_URL", VAULT_URL)
    monkeypatch.setenv("LOCKER_API_KEY", API_KEY)

    result = runner.invoke(app, [str(tmp_path / "missing.txt")])

    assert result.exit_code == 1
    assert "missing.txt" in result.output


def test_missing_vault_url(tmp_path, monkeypatch):
    monkeypatch.delenv("LOCKER_VAULT_URL", raising=False)
    monkeypatch.setenv("LOCKER_API_KEY", API_KEY)

    skill_file = tmp_path / "test.txt"
    skill_file.write_text("content")

    result = runner.invoke(app, [str(skill_file)])

    assert result.exit_code == 1
    assert "LOCKER_VAULT_URL" in result.output


def test_missing_api_key(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCKER_VAULT_URL", VAULT_URL)
    monkeypatch.delenv("LOCKER_API_KEY", raising=False)

    skill_file = tmp_path / "test.txt"
    skill_file.write_text("content")

    result = runner.invoke(app, [str(skill_file)])

    assert result.exit_code == 1
    assert "LOCKER_API_KEY" in result.output


def test_server_returns_409(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCKER_VAULT_URL", VAULT_URL)
    monkeypatch.setenv("LOCKER_API_KEY", API_KEY)

    skill_file = tmp_path / "dup-skill.txt"
    skill_file.write_text("content")

    with respx.mock:
        respx.post(f"{VAULT_URL}/api/v1/skills").mock(
            return_value=httpx.Response(409, json={"detail": "Skill name already exists"})
        )
        result = runner.invoke(app, [str(skill_file)])

    assert result.exit_code == 1
    assert "409" in result.output


def test_server_returns_401(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCKER_VAULT_URL", VAULT_URL)
    monkeypatch.setenv("LOCKER_API_KEY", "bad-key")

    skill_file = tmp_path / "some-skill.txt"
    skill_file.write_text("content")

    with respx.mock:
        respx.post(f"{VAULT_URL}/api/v1/skills").mock(
            return_value=httpx.Response(401, json={"detail": "Invalid API key"})
        )
        result = runner.invoke(app, [str(skill_file)])

    assert result.exit_code == 1
    assert "401" in result.output


# ── Folder deploy tests ──────────────────────────────────────────────


FOLDER_RESPONSE = {
    "id": "xyz",
    "name": "my-skill",
    "file_count": 2,
    "created_at": "2026-03-04T00:00:00Z",
}


def test_folder_deploy_success(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCKER_VAULT_URL", VAULT_URL)
    monkeypatch.setenv("LOCKER_API_KEY", API_KEY)

    # Create sibling .md file
    sibling = tmp_path / "my-skill.md"
    sibling.write_text("Main skill content goes here.")

    # Create references folder
    folder = tmp_path / "my-skill"
    refs = folder / "references"
    refs.mkdir(parents=True)
    (refs / "guide.md").write_text("Guide content")
    (refs / "examples.md").write_text("Examples content")

    with respx.mock:
        route = respx.post(f"{VAULT_URL}/api/v1/skills/deploy-folder").mock(
            return_value=httpx.Response(201, json=FOLDER_RESPONSE)
        )
        result = runner.invoke(app, [str(folder)])

    assert result.exit_code == 0
    assert "my-skill" in result.output
    assert "2 reference file(s)" in result.output

    # Verify the request body sent to the server
    import json

    body = json.loads(route.calls[0].request.content)
    assert len(body["files"]) == 2


def test_folder_deploy_missing_sibling_md(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCKER_VAULT_URL", VAULT_URL)
    monkeypatch.setenv("LOCKER_API_KEY", API_KEY)

    # Create folder without a sibling .md file
    folder = tmp_path / "no-md"
    folder.mkdir()
    (folder / "somefile.txt").write_text("content")

    result = runner.invoke(app, [str(folder)])

    assert result.exit_code == 1
    assert "no-md.md" in result.output


def test_folder_deploy_missing_folder(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCKER_VAULT_URL", VAULT_URL)
    monkeypatch.setenv("LOCKER_API_KEY", API_KEY)

    result = runner.invoke(app, [str(tmp_path / "nonexistent")])

    assert result.exit_code == 1


def test_single_file_deploy_still_works(tmp_path, monkeypatch):
    """Confirm single-file deploy continues to work via the is_dir() routing."""
    monkeypatch.setenv("LOCKER_VAULT_URL", VAULT_URL)
    monkeypatch.setenv("LOCKER_API_KEY", API_KEY)

    skill_file = tmp_path / "quick-reply.txt"
    skill_file.write_text("Reply to all emails politely.")

    with respx.mock:
        respx.post(f"{VAULT_URL}/api/v1/skills").mock(
            return_value=httpx.Response(201, json=SKILL_RESPONSE)
        )
        result = runner.invoke(app, [str(skill_file)])

    assert result.exit_code == 0
    assert 'Deployed skill "quick-reply"' in result.output
