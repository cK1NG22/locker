import json

import httpx
import pytest
import respx
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()

VAULT_URL = "http://localhost:8000"
JWT_TOKEN = "eytest.dummy.token"
SKILL_RESPONSE = {"id": "abc123", "name": "email-style", "created_at": "2024-01-01"}


@pytest.fixture()
def cli_env(monkeypatch):
    monkeypatch.setenv("LOCKER_VAULT_URL", VAULT_URL)
    monkeypatch.setenv("LOCKER_JWT_TOKEN", JWT_TOKEN)


def test_successful_deploy(tmp_path, cli_env):

    skill_file = tmp_path / "email-style.txt"
    skill_file.write_text("Always write concise emails.")

    with respx.mock:
        respx.post(f"{VAULT_URL}/api/v1/skills").mock(
            return_value=httpx.Response(201, json=SKILL_RESPONSE)
        )
        result = runner.invoke(app, ["deploy", str(skill_file)])

    assert result.exit_code == 0
    assert 'Deployed skill "email-style" (id: abc123)' in result.output


def test_file_not_found(tmp_path, cli_env):
    result = runner.invoke(app, ["deploy", str(tmp_path / "missing.txt")])

    assert result.exit_code == 1
    assert "missing.txt" in result.output


def test_missing_vault_url(tmp_path, monkeypatch):
    monkeypatch.delenv("LOCKER_VAULT_URL", raising=False)
    monkeypatch.setenv("LOCKER_JWT_TOKEN", JWT_TOKEN)

    skill_file = tmp_path / "test.txt"
    skill_file.write_text("content")

    result = runner.invoke(app, ["deploy", str(skill_file)])

    assert result.exit_code == 1
    assert "LOCKER_VAULT_URL" in result.output


def test_missing_jwt_token(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCKER_VAULT_URL", VAULT_URL)
    monkeypatch.delenv("LOCKER_JWT_TOKEN", raising=False)
    monkeypatch.delenv("LOCKER_API_KEY", raising=False)

    skill_file = tmp_path / "test.txt"
    skill_file.write_text("content")

    result = runner.invoke(app, ["deploy", str(skill_file)])

    assert result.exit_code == 1
    assert "LOCKER_API_KEY" in result.output or "LOCKER_JWT_TOKEN" in result.output


def test_server_returns_409(tmp_path, cli_env):

    skill_file = tmp_path / "dup-skill.txt"
    skill_file.write_text("content")

    with respx.mock:
        respx.post(f"{VAULT_URL}/api/v1/skills").mock(
            return_value=httpx.Response(409, json={"detail": "Skill name already exists"})
        )
        result = runner.invoke(app, ["deploy", str(skill_file)])

    assert result.exit_code == 1
    assert "409" in result.output


def test_server_returns_401(tmp_path, monkeypatch, cli_env):
    monkeypatch.setenv("LOCKER_JWT_TOKEN", "bad-token")

    skill_file = tmp_path / "some-skill.txt"
    skill_file.write_text("content")

    with respx.mock:
        respx.post(f"{VAULT_URL}/api/v1/skills").mock(
            return_value=httpx.Response(401, json={"detail": "Invalid API key"})
        )
        result = runner.invoke(app, ["deploy", str(skill_file)])

    assert result.exit_code == 1
    assert "401" in result.output


# ── Visibility flag tests ────────────────────────────────────────────


def test_deploy_with_visibility_flag(tmp_path, cli_env):

    skill_file = tmp_path / "my-skill.txt"
    skill_file.write_text("content")

    with respx.mock:
        route = respx.post(f"{VAULT_URL}/api/v1/skills").mock(
            return_value=httpx.Response(201, json=SKILL_RESPONSE)
        )
        result = runner.invoke(app, ["deploy", str(skill_file), "--visibility", "hidden"])

    assert result.exit_code == 0
    body = json.loads(route.calls[0].request.content)
    assert body["visibility"] == "hidden"


def test_deploy_invalid_visibility(tmp_path, cli_env):

    skill_file = tmp_path / "my-skill.txt"
    skill_file.write_text("content")

    result = runner.invoke(app, ["deploy", str(skill_file), "--visibility", "invalid"])

    assert result.exit_code == 1
    assert "Invalid visibility" in result.output


def test_deploy_without_visibility_omits_field(tmp_path, cli_env):

    skill_file = tmp_path / "my-skill.txt"
    skill_file.write_text("content")

    with respx.mock:
        route = respx.post(f"{VAULT_URL}/api/v1/skills").mock(
            return_value=httpx.Response(201, json=SKILL_RESPONSE)
        )
        result = runner.invoke(app, ["deploy", str(skill_file)])

    assert result.exit_code == 0
    body = json.loads(route.calls[0].request.content)
    assert "visibility" not in body


# ── Folder deploy tests ──────────────────────────────────────────────


FOLDER_RESPONSE = {
    "id": "xyz",
    "name": "my-skill",
    "file_count": 2,
    "created_at": "2026-03-04T00:00:00Z",
}


def test_folder_deploy_success(tmp_path, cli_env):

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
        result = runner.invoke(app, ["deploy", str(folder)])

    assert result.exit_code == 0
    assert "my-skill" in result.output
    assert "2 reference file(s)" in result.output

    # Verify the request body sent to the server
    import json

    body = json.loads(route.calls[0].request.content)
    assert len(body["files"]) == 2


def test_folder_deploy_missing_sibling_md(tmp_path, cli_env):

    # Create folder without a sibling .md file
    folder = tmp_path / "no-md"
    folder.mkdir()
    (folder / "somefile.txt").write_text("content")

    result = runner.invoke(app, ["deploy", str(folder)])

    assert result.exit_code == 1
    assert "no-md.md" in result.output


def test_folder_deploy_missing_folder(tmp_path, cli_env):

    result = runner.invoke(app, ["deploy", str(tmp_path / "nonexistent")])

    assert result.exit_code == 1


def test_single_file_deploy_still_works(tmp_path, cli_env):
    """Confirm single-file deploy continues to work via the is_dir() routing."""

    skill_file = tmp_path / "quick-reply.txt"
    skill_file.write_text("Reply to all emails politely.")

    with respx.mock:
        respx.post(f"{VAULT_URL}/api/v1/skills").mock(
            return_value=httpx.Response(201, json=SKILL_RESPONSE)
        )
        result = runner.invoke(app, ["deploy", str(skill_file)])

    assert result.exit_code == 0
    assert 'Deployed skill "quick-reply"' in result.output


# ── Sync tests ────────────────────────────────────────────────────────

TEAM_TOKEN = "test-team-token"
SYNC_RESPONSE = {
    "team": "Legal",
    "skills": [
        {"name": "email-style", "description": "Write concise emails", "content": "Always be concise."},
        {"name": "brief-format", "description": "Format legal briefs", "content": "Use IRAC structure."},
    ],
}
MIXED_SYNC_RESPONSE = {
    "team": "Legal",
    "skills": [
        {"name": "open-skill", "description": None, "content": "Open content."},
        {"name": "shared-skill", "description": "A shared skill", "content": None},
    ],
}


def test_sync_success(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCKER_VAULT_URL", VAULT_URL)
    monkeypatch.setenv("LOCKER_TEAM_TOKEN", TEAM_TOKEN)

    with respx.mock:
        respx.get(f"{VAULT_URL}/api/v1/employee/skills").mock(
            return_value=httpx.Response(200, json=SYNC_RESPONSE)
        )
        result = runner.invoke(app, ["sync", "--output-dir", str(tmp_path)])

    assert result.exit_code == 0
    assert "email-style" in result.output
    assert "brief-format" in result.output
    assert "Synced 2 skill(s)" in result.output
    assert (tmp_path / "email-style.md").read_text() == "Always be concise."
    assert (tmp_path / "brief-format.md").read_text() == "Use IRAC structure."


def test_sync_shared_skills_skipped(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCKER_VAULT_URL", VAULT_URL)
    monkeypatch.setenv("LOCKER_TEAM_TOKEN", TEAM_TOKEN)

    with respx.mock:
        respx.get(f"{VAULT_URL}/api/v1/employee/skills").mock(
            return_value=httpx.Response(200, json=MIXED_SYNC_RESPONSE)
        )
        result = runner.invoke(app, ["sync", "--output-dir", str(tmp_path)])

    assert result.exit_code == 0
    assert "open-skill" in result.output
    assert "shared-skill" in result.output
    assert "skipped" in result.output
    assert (tmp_path / "open-skill.md").exists()
    assert not (tmp_path / "shared-skill.md").exists()
    assert "Synced 1 skill(s)" in result.output


def test_sync_missing_vault_url(tmp_path, monkeypatch):
    monkeypatch.delenv("LOCKER_VAULT_URL", raising=False)
    monkeypatch.setenv("LOCKER_TEAM_TOKEN", TEAM_TOKEN)

    result = runner.invoke(app, ["sync", "--output-dir", str(tmp_path)])

    assert result.exit_code == 1
    assert "LOCKER_VAULT_URL" in result.output


def test_sync_missing_team_token(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCKER_VAULT_URL", VAULT_URL)
    monkeypatch.delenv("LOCKER_TEAM_TOKEN", raising=False)

    result = runner.invoke(app, ["sync", "--output-dir", str(tmp_path)])

    assert result.exit_code == 1
    assert "LOCKER_TEAM_TOKEN" in result.output


def test_sync_server_unreachable(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCKER_VAULT_URL", VAULT_URL)
    monkeypatch.setenv("LOCKER_TEAM_TOKEN", TEAM_TOKEN)

    with respx.mock:
        respx.get(f"{VAULT_URL}/api/v1/employee/skills").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )
        result = runner.invoke(app, ["sync", "--output-dir", str(tmp_path)])

    assert result.exit_code == 1
    assert "Error" in result.output


def test_sync_unauthorized(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCKER_VAULT_URL", VAULT_URL)
    monkeypatch.setenv("LOCKER_TEAM_TOKEN", "bad-token")

    with respx.mock:
        respx.get(f"{VAULT_URL}/api/v1/employee/skills").mock(
            return_value=httpx.Response(401, json={"detail": "Unauthorized"})
        )
        result = runner.invoke(app, ["sync", "--output-dir", str(tmp_path)])

    assert result.exit_code == 1
    assert "401" in result.output


def test_sync_idempotent(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCKER_VAULT_URL", VAULT_URL)
    monkeypatch.setenv("LOCKER_TEAM_TOKEN", TEAM_TOKEN)

    with respx.mock:
        respx.get(f"{VAULT_URL}/api/v1/employee/skills").mock(
            return_value=httpx.Response(200, json=SYNC_RESPONSE)
        )
        runner.invoke(app, ["sync", "--output-dir", str(tmp_path)])

    # Second sync with updated content
    updated_response = {
        "team": "Legal",
        "skills": [{"name": "email-style", "description": None, "content": "Updated content."}],
    }
    with respx.mock:
        respx.get(f"{VAULT_URL}/api/v1/employee/skills").mock(
            return_value=httpx.Response(200, json=updated_response)
        )
        result = runner.invoke(app, ["sync", "--output-dir", str(tmp_path)])

    assert result.exit_code == 0
    assert (tmp_path / "email-style.md").read_text() == "Updated content."


def test_sync_creates_output_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCKER_VAULT_URL", VAULT_URL)
    monkeypatch.setenv("LOCKER_TEAM_TOKEN", TEAM_TOKEN)

    new_dir = tmp_path / "nested" / "commands"
    assert not new_dir.exists()

    with respx.mock:
        respx.get(f"{VAULT_URL}/api/v1/employee/skills").mock(
            return_value=httpx.Response(200, json=SYNC_RESPONSE)
        )
        result = runner.invoke(app, ["sync", "--output-dir", str(new_dir)])

    assert result.exit_code == 0
    assert new_dir.exists()


# ── Setup tests ──────────────────────────────────────────────────────


SKILL_CONTENT = "# /locker skill router\nRoute to the right skill."
SKILL_URL = "https://raw.githubusercontent.com/ck22coding/locker-skill/main/locker.md"


def test_setup_creates_claude_json(tmp_path, monkeypatch):
    claude_json = tmp_path / ".claude.json"
    commands_dir = tmp_path / ".claude" / "commands"
    monkeypatch.setattr("cli.setup.CLAUDE_JSON_PATH", claude_json)
    monkeypatch.setattr("cli.setup.COMMANDS_DIR", commands_dir)

    with respx.mock:
        respx.get(SKILL_URL).mock(return_value=httpx.Response(200, text=SKILL_CONTENT))
        result = runner.invoke(app, ["setup", "--token", "my-team-token"])

    assert result.exit_code == 0
    config = json.loads(claude_json.read_text())
    assert config["mcpServers"]["locker"]["type"] == "sse"
    assert config["mcpServers"]["locker"]["url"] == "https://locker.up.railway.app/mcp"
    assert config["mcpServers"]["locker"]["headers"]["X-Team-Token"] == "my-team-token"
    assert (commands_dir / "locker.md").read_text() == SKILL_CONTENT


def test_setup_preserves_existing_config(tmp_path, monkeypatch):
    claude_json = tmp_path / ".claude.json"
    commands_dir = tmp_path / ".claude" / "commands"
    claude_json.write_text(json.dumps({"existingKey": "value", "mcpServers": {"other": {"url": "http://other"}}}))
    monkeypatch.setattr("cli.setup.CLAUDE_JSON_PATH", claude_json)
    monkeypatch.setattr("cli.setup.COMMANDS_DIR", commands_dir)

    with respx.mock:
        respx.get(SKILL_URL).mock(return_value=httpx.Response(200, text=SKILL_CONTENT))
        result = runner.invoke(app, ["setup", "--token", "tok"])

    assert result.exit_code == 0
    config = json.loads(claude_json.read_text())
    assert config["existingKey"] == "value"
    assert "other" in config["mcpServers"]
    assert "locker" in config["mcpServers"]


def test_setup_custom_url(tmp_path, monkeypatch):
    claude_json = tmp_path / ".claude.json"
    commands_dir = tmp_path / ".claude" / "commands"
    monkeypatch.setattr("cli.setup.CLAUDE_JSON_PATH", claude_json)
    monkeypatch.setattr("cli.setup.COMMANDS_DIR", commands_dir)

    with respx.mock:
        respx.get(SKILL_URL).mock(return_value=httpx.Response(200, text=SKILL_CONTENT))
        result = runner.invoke(app, ["setup", "--url", "http://localhost:8000", "--token", "tok"])

    assert result.exit_code == 0
    config = json.loads(claude_json.read_text())
    assert config["mcpServers"]["locker"]["url"] == "http://localhost:8000/mcp"


def test_setup_overwrites_existing_locker_entry(tmp_path, monkeypatch):
    claude_json = tmp_path / ".claude.json"
    commands_dir = tmp_path / ".claude" / "commands"
    claude_json.write_text(json.dumps({"mcpServers": {"locker": {"url": "http://old/mcp"}}}))
    monkeypatch.setattr("cli.setup.CLAUDE_JSON_PATH", claude_json)
    monkeypatch.setattr("cli.setup.COMMANDS_DIR", commands_dir)

    with respx.mock:
        respx.get(SKILL_URL).mock(return_value=httpx.Response(200, text=SKILL_CONTENT))
        result = runner.invoke(app, ["setup", "--token", "new-token"])

    assert result.exit_code == 0
    config = json.loads(claude_json.read_text())
    assert config["mcpServers"]["locker"]["headers"]["X-Team-Token"] == "new-token"


def test_setup_skill_download_failure_non_fatal(tmp_path, monkeypatch):
    """Setup should succeed even if skill download fails."""
    claude_json = tmp_path / ".claude.json"
    commands_dir = tmp_path / ".claude" / "commands"
    monkeypatch.setattr("cli.setup.CLAUDE_JSON_PATH", claude_json)
    monkeypatch.setattr("cli.setup.COMMANDS_DIR", commands_dir)

    with respx.mock:
        respx.get(SKILL_URL).mock(return_value=httpx.Response(404))
        result = runner.invoke(app, ["setup", "--token", "tok"])

    assert result.exit_code == 0
    assert claude_json.exists()
    assert not (commands_dir / "locker.md").exists()
    assert "Warning" in result.output


# ── Join tests ────────────────────────────────────────────────────────

JOIN_URL = "https://locker.up.railway.app"
JOIN_API = f"{JOIN_URL}/api/v1/invite/join-cli"
JOIN_RESPONSE = {
    "team_name": "ACME Corp",
    "team_token": "test-team-uuid",
    "server_url": JOIN_URL,
    "skill_count": 5,
}


def test_join_cli_valid_code(tmp_path, monkeypatch):
    claude_json = tmp_path / ".claude.json"
    desktop_config = tmp_path / "Claude" / "claude_desktop_config.json"
    commands_dir = tmp_path / ".claude" / "commands"
    monkeypatch.setattr("cli.setup.CLAUDE_JSON_PATH", claude_json)
    monkeypatch.setattr("cli.setup.CLAUDE_DESKTOP_CONFIG_PATH", desktop_config)
    monkeypatch.setattr("cli.setup.COMMANDS_DIR", commands_dir)

    with respx.mock:
        respx.post(JOIN_API).mock(return_value=httpx.Response(200, json=JOIN_RESPONSE))
        respx.get(SKILL_URL).mock(return_value=httpx.Response(200, text=SKILL_CONTENT))
        result = runner.invoke(app, ["join", "ACME-7X3K"])

    assert result.exit_code == 0
    assert "ACME Corp" in result.output
    assert "5 skills" in result.output
    config = json.loads(claude_json.read_text())
    assert config["mcpServers"]["locker"]["headers"]["X-Team-Token"] == "test-team-uuid"


def test_join_cli_invalid_code(tmp_path, monkeypatch):
    claude_json = tmp_path / ".claude.json"
    desktop_config = tmp_path / "Claude" / "claude_desktop_config.json"
    commands_dir = tmp_path / ".claude" / "commands"
    monkeypatch.setattr("cli.setup.CLAUDE_JSON_PATH", claude_json)
    monkeypatch.setattr("cli.setup.CLAUDE_DESKTOP_CONFIG_PATH", desktop_config)
    monkeypatch.setattr("cli.setup.COMMANDS_DIR", commands_dir)

    with respx.mock:
        respx.post(JOIN_API).mock(
            return_value=httpx.Response(404, json={"detail": "Invalid invite code"})
        )
        result = runner.invoke(app, ["join", "BAD-CODE"])

    assert result.exit_code == 1
    assert "Invalid invite code" in result.output


def test_join_cli_null_token(tmp_path, monkeypatch):
    claude_json = tmp_path / ".claude.json"
    desktop_config = tmp_path / "Claude" / "claude_desktop_config.json"
    commands_dir = tmp_path / ".claude" / "commands"
    monkeypatch.setattr("cli.setup.CLAUDE_JSON_PATH", claude_json)
    monkeypatch.setattr("cli.setup.CLAUDE_DESKTOP_CONFIG_PATH", desktop_config)
    monkeypatch.setattr("cli.setup.COMMANDS_DIR", commands_dir)

    with respx.mock:
        respx.post(JOIN_API).mock(
            return_value=httpx.Response(404, json={"detail": "Team setup incomplete — ask admin to rotate the team token"})
        )
        result = runner.invoke(app, ["join", "ACME-7X3K"])

    assert result.exit_code == 1
    assert "ask admin" in result.output


def test_join_cli_decrypt_failure(tmp_path, monkeypatch):
    claude_json = tmp_path / ".claude.json"
    desktop_config = tmp_path / "Claude" / "claude_desktop_config.json"
    commands_dir = tmp_path / ".claude" / "commands"
    monkeypatch.setattr("cli.setup.CLAUDE_JSON_PATH", claude_json)
    monkeypatch.setattr("cli.setup.CLAUDE_DESKTOP_CONFIG_PATH", desktop_config)
    monkeypatch.setattr("cli.setup.COMMANDS_DIR", commands_dir)

    with respx.mock:
        respx.post(JOIN_API).mock(
            return_value=httpx.Response(500, json={"detail": "Failed to decrypt team token — contact admin"})
        )
        result = runner.invoke(app, ["join", "ACME-7X3K"])

    assert result.exit_code == 1
    assert "decrypt" in result.output.lower() or "contact admin" in result.output.lower()


def test_join_writes_claude_code_config(tmp_path, monkeypatch):
    claude_json = tmp_path / ".claude.json"
    desktop_config = tmp_path / "Claude" / "claude_desktop_config.json"
    commands_dir = tmp_path / ".claude" / "commands"
    monkeypatch.setattr("cli.setup.CLAUDE_JSON_PATH", claude_json)
    monkeypatch.setattr("cli.setup.CLAUDE_DESKTOP_CONFIG_PATH", desktop_config)
    monkeypatch.setattr("cli.setup.COMMANDS_DIR", commands_dir)

    with respx.mock:
        respx.post(JOIN_API).mock(return_value=httpx.Response(200, json=JOIN_RESPONSE))
        respx.get(SKILL_URL).mock(return_value=httpx.Response(200, text=SKILL_CONTENT))
        runner.invoke(app, ["join", "ACME-7X3K"])

    config = json.loads(claude_json.read_text())
    assert config["mcpServers"]["locker"]["type"] == "sse"
    assert config["mcpServers"]["locker"]["url"] == f"{JOIN_URL}/mcp"
    assert config["mcpServers"]["locker"]["headers"]["X-Team-Token"] == "test-team-uuid"


def test_join_writes_claude_desktop_config(tmp_path, monkeypatch):
    claude_json = tmp_path / ".claude.json"
    desktop_config = tmp_path / "Claude" / "claude_desktop_config.json"
    commands_dir = tmp_path / ".claude" / "commands"
    monkeypatch.setattr("cli.setup.CLAUDE_JSON_PATH", claude_json)
    monkeypatch.setattr("cli.setup.CLAUDE_DESKTOP_CONFIG_PATH", desktop_config)
    monkeypatch.setattr("cli.setup.COMMANDS_DIR", commands_dir)

    with respx.mock:
        respx.post(JOIN_API).mock(return_value=httpx.Response(200, json=JOIN_RESPONSE))
        respx.get(SKILL_URL).mock(return_value=httpx.Response(200, text=SKILL_CONTENT))
        runner.invoke(app, ["join", "ACME-7X3K"])

    assert desktop_config.exists()
    config = json.loads(desktop_config.read_text())
    assert config["mcpServers"]["locker"]["type"] == "sse"
    assert config["mcpServers"]["locker"]["url"] == f"{JOIN_URL}/mcp"
    assert config["mcpServers"]["locker"]["headers"]["X-Team-Token"] == "test-team-uuid"


def test_join_server_unreachable(tmp_path, monkeypatch):
    claude_json = tmp_path / ".claude.json"
    desktop_config = tmp_path / "Claude" / "claude_desktop_config.json"
    commands_dir = tmp_path / ".claude" / "commands"
    monkeypatch.setattr("cli.setup.CLAUDE_JSON_PATH", claude_json)
    monkeypatch.setattr("cli.setup.CLAUDE_DESKTOP_CONFIG_PATH", desktop_config)
    monkeypatch.setattr("cli.setup.COMMANDS_DIR", commands_dir)

    with respx.mock:
        respx.post(JOIN_API).mock(side_effect=httpx.ConnectError("Connection refused"))
        result = runner.invoke(app, ["join", "ACME-7X3K"])

    assert result.exit_code == 1
    assert "Could not reach server" in result.output
    assert not claude_json.exists()


def test_join_preserves_existing_config(tmp_path, monkeypatch):
    claude_json = tmp_path / ".claude.json"
    claude_json.write_text(json.dumps({"existingKey": "keep", "mcpServers": {"other-server": {"url": "http://other"}}}))
    desktop_config = tmp_path / "Claude" / "claude_desktop_config.json"
    desktop_config.parent.mkdir(parents=True, exist_ok=True)
    desktop_config.write_text(json.dumps({"mcpServers": {"another": {"url": "http://x"}}}))
    commands_dir = tmp_path / ".claude" / "commands"
    monkeypatch.setattr("cli.setup.CLAUDE_JSON_PATH", claude_json)
    monkeypatch.setattr("cli.setup.CLAUDE_DESKTOP_CONFIG_PATH", desktop_config)
    monkeypatch.setattr("cli.setup.COMMANDS_DIR", commands_dir)

    with respx.mock:
        respx.post(JOIN_API).mock(return_value=httpx.Response(200, json=JOIN_RESPONSE))
        respx.get(SKILL_URL).mock(return_value=httpx.Response(200, text=SKILL_CONTENT))
        result = runner.invoke(app, ["join", "ACME-7X3K"])

    assert result.exit_code == 0
    # Claude Code config preserved
    cc = json.loads(claude_json.read_text())
    assert cc["existingKey"] == "keep"
    assert "other-server" in cc["mcpServers"]
    assert "locker" in cc["mcpServers"]
    # Desktop config preserved
    dc = json.loads(desktop_config.read_text())
    assert "another" in dc["mcpServers"]
    assert "locker" in dc["mcpServers"]
