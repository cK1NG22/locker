from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from tests.conftest import TEST_JWT, TEST_JWT_SECRET, OTHER_JWT

import jwt as _jwt

from main import app
from vault.db import init_db, close_db

HEADERS = {"Authorization": f"Bearer {TEST_JWT}"}
BAD_HEADERS = {"Authorization": "Bearer invalid-token"}


@pytest_asyncio.fixture
async def client():
    await init_db()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
    await close_db()


# --- Auth ---

@pytest.mark.asyncio
async def test_no_token_returns_401(client):
    r = await client.get("/api/v1/skills")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_invalid_token_returns_401(client):
    r = await client.get("/api/v1/skills", headers=BAD_HEADERS)
    assert r.status_code == 401


# --- Create ---

@pytest.mark.asyncio
async def test_create_skill(client):
    r = await client.post(
        "/api/v1/skills",
        json={"name": "test-skill", "content": "Do the thing."},
        headers=HEADERS,
    )
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["name"] == "test-skill"
    assert data["visibility"] == "open"
    assert "created_at" in data
    assert "content" not in data


@pytest.mark.asyncio
async def test_create_skill_with_visibility(client):
    r = await client.post(
        "/api/v1/skills",
        json={"name": "open-skill", "content": "visible", "visibility": "open"},
        headers=HEADERS,
    )
    assert r.status_code == 201
    assert r.json()["visibility"] == "open"
    skill_id = r.json()["id"]
    fetched = await client.get(f"/api/v1/skills/{skill_id}", headers=HEADERS)
    assert fetched.json()["visibility"] == "open"


@pytest.mark.asyncio
async def test_create_skill_invalid_visibility(client):
    r = await client.post(
        "/api/v1/skills",
        json={"name": "bad-vis", "content": "x", "visibility": "bogus"},
        headers=HEADERS,
    )
    assert r.status_code == 422


# --- List ---

@pytest.mark.asyncio
async def test_list_skills_no_content(client):
    await client.post(
        "/api/v1/skills",
        json={"name": "list-skill", "content": "secret text"},
        headers=HEADERS,
    )
    r = await client.get("/api/v1/skills", headers=HEADERS)
    assert r.status_code == 200
    skills = r.json()["skills"]
    assert any(s["name"] == "list-skill" for s in skills)
    for s in skills:
        assert "content" not in s
        assert "visibility" in s


# --- Get by ID ---

@pytest.mark.asyncio
async def test_get_skill_by_id(client):
    create = await client.post(
        "/api/v1/skills",
        json={"name": "fetch-skill", "content": "fetch me"},
        headers=HEADERS,
    )
    skill_id = create.json()["id"]
    r = await client.get(f"/api/v1/skills/{skill_id}", headers=HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert data["content"] == "fetch me"
    assert data["id"] == skill_id
    assert data["visibility"] == "open"


@pytest.mark.asyncio
async def test_get_missing_id_returns_404(client):
    r = await client.get("/api/v1/skills/nonexistent-id", headers=HEADERS)
    assert r.status_code == 404


# --- Get by name ---

@pytest.mark.asyncio
async def test_get_skill_by_name(client):
    await client.post(
        "/api/v1/skills",
        json={"name": "named-skill", "content": "named content"},
        headers=HEADERS,
    )
    r = await client.get("/api/v1/skills?name=named-skill", headers=HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert data["content"] == "named content"
    assert data["name"] == "named-skill"
    assert data["visibility"] == "open"


@pytest.mark.asyncio
async def test_get_missing_name_returns_404(client):
    r = await client.get("/api/v1/skills?name=does-not-exist", headers=HEADERS)
    assert r.status_code == 404


# --- Update ---

@pytest.mark.asyncio
async def test_update_name_only(client):
    create = await client.post(
        "/api/v1/skills",
        json={"name": "old-name", "content": "keep this content"},
        headers=HEADERS,
    )
    skill_id = create.json()["id"]
    r = await client.put(
        f"/api/v1/skills/{skill_id}",
        json={"name": "new-name"},
        headers=HEADERS,
    )
    assert r.status_code == 200
    assert r.json()["name"] == "new-name"
    fetched = await client.get(f"/api/v1/skills/{skill_id}", headers=HEADERS)
    assert fetched.json()["content"] == "keep this content"


@pytest.mark.asyncio
async def test_update_content_only(client):
    create = await client.post(
        "/api/v1/skills",
        json={"name": "content-update-skill", "content": "old content"},
        headers=HEADERS,
    )
    skill_id = create.json()["id"]
    r = await client.put(
        f"/api/v1/skills/{skill_id}",
        json={"content": "new content"},
        headers=HEADERS,
    )
    assert r.status_code == 200
    fetched = await client.get(f"/api/v1/skills/{skill_id}", headers=HEADERS)
    assert fetched.json()["content"] == "new content"


@pytest.mark.asyncio
async def test_update_changes_updated_at(client):
    create = await client.post(
        "/api/v1/skills",
        json={"name": "ts-skill", "content": "ts content"},
        headers=HEADERS,
    )
    skill_id = create.json()["id"]
    original_ts = create.json()["created_at"]
    r = await client.put(
        f"/api/v1/skills/{skill_id}",
        json={"name": "ts-skill-updated"},
        headers=HEADERS,
    )
    assert r.json()["updated_at"] >= original_ts


@pytest.mark.asyncio
async def test_update_visibility(client):
    create = await client.post(
        "/api/v1/skills",
        json={"name": "vis-update-skill", "content": "content"},
        headers=HEADERS,
    )
    skill_id = create.json()["id"]
    r = await client.put(
        f"/api/v1/skills/{skill_id}",
        json={"visibility": "shared"},
        headers=HEADERS,
    )
    assert r.status_code == 200
    assert r.json()["visibility"] == "shared"
    fetched = await client.get(f"/api/v1/skills/{skill_id}", headers=HEADERS)
    assert fetched.json()["visibility"] == "shared"


# --- Delete ---

@pytest.mark.asyncio
async def test_delete_skill(client):
    create = await client.post(
        "/api/v1/skills",
        json={"name": "delete-me", "content": "bye"},
        headers=HEADERS,
    )
    skill_id = create.json()["id"]
    r = await client.delete(f"/api/v1/skills/{skill_id}", headers=HEADERS)
    assert r.status_code == 204
    r2 = await client.get(f"/api/v1/skills/{skill_id}", headers=HEADERS)
    assert r2.status_code == 404


@pytest.mark.asyncio
async def test_delete_missing_returns_404(client):
    r = await client.delete("/api/v1/skills/no-such-id", headers=HEADERS)
    assert r.status_code == 404


# --- Bundle ---

@pytest.mark.asyncio
async def test_bundle_includes_content(client):
    await client.post(
        "/api/v1/skills",
        json={"name": "bundle-skill", "content": "bundled content"},
        headers=HEADERS,
    )
    r = await client.get("/api/v1/skills/bundle", headers=HEADERS)
    assert r.status_code == 200
    skills = r.json()["skills"]
    matching = [s for s in skills if s["name"] == "bundle-skill"]
    assert len(matching) == 1
    assert matching[0]["content"] == "bundled content"


# --- Skill files ---


async def _make_skill(client, name="file-test-skill"):
    r = await client.post(
        "/api/v1/skills",
        json={"name": name, "content": "main content"},
        headers=HEADERS,
    )
    return r.json()["id"]


@pytest.mark.asyncio
async def test_upload_and_list_skill_file(client):
    skill_id = await _make_skill(client, "file-list-skill")
    r = await client.post(
        f"/api/v1/skills/{skill_id}/files",
        json={"path": "references/guide.md", "content": "Guide content here"},
        headers=HEADERS,
    )
    assert r.status_code == 201
    data = r.json()
    assert data["path"] == "references/guide.md"
    assert data["size_bytes"] == len("Guide content here".encode())

    r2 = await client.get(f"/api/v1/skills/{skill_id}/files", headers=HEADERS)
    assert r2.status_code == 200
    files = r2.json()["files"]
    assert len(files) == 1
    assert files[0]["path"] == "references/guide.md"


@pytest.mark.asyncio
async def test_get_skill_file_content(client):
    skill_id = await _make_skill(client, "file-get-skill")
    cr = await client.post(
        f"/api/v1/skills/{skill_id}/files",
        json={"path": "ref.md", "content": "Secret ref content"},
        headers=HEADERS,
    )
    file_id = cr.json()["id"]
    r = await client.get(f"/api/v1/skills/{skill_id}/files/{file_id}", headers=HEADERS)
    assert r.status_code == 200
    assert r.json()["content"] == "Secret ref content"
    assert r.json()["path"] == "ref.md"


@pytest.mark.asyncio
async def test_delete_skill_file(client):
    skill_id = await _make_skill(client, "file-del-skill")
    cr = await client.post(
        f"/api/v1/skills/{skill_id}/files",
        json={"path": "to-delete.md", "content": "bye"},
        headers=HEADERS,
    )
    file_id = cr.json()["id"]
    r = await client.delete(f"/api/v1/skills/{skill_id}/files/{file_id}", headers=HEADERS)
    assert r.status_code == 204
    r2 = await client.get(f"/api/v1/skills/{skill_id}/files/{file_id}", headers=HEADERS)
    assert r2.status_code == 404


@pytest.mark.asyncio
async def test_duplicate_file_path_returns_409(client):
    skill_id = await _make_skill(client, "file-dup-skill")
    await client.post(
        f"/api/v1/skills/{skill_id}/files",
        json={"path": "same.md", "content": "first"},
        headers=HEADERS,
    )
    r = await client.post(
        f"/api/v1/skills/{skill_id}/files",
        json={"path": "same.md", "content": "second"},
        headers=HEADERS,
    )
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_file_on_missing_skill_returns_404(client):
    r = await client.get("/api/v1/skills/nonexistent/files", headers=HEADERS)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_skill_detail_includes_files(client):
    skill_id = await _make_skill(client, "detail-files-skill")
    await client.post(
        f"/api/v1/skills/{skill_id}/files",
        json={"path": "ref1.md", "content": "ref1"},
        headers=HEADERS,
    )
    await client.post(
        f"/api/v1/skills/{skill_id}/files",
        json={"path": "ref2.md", "content": "ref2 longer"},
        headers=HEADERS,
    )
    r = await client.get(f"/api/v1/skills/{skill_id}", headers=HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert len(data["files"]) == 2
    paths = {f["path"] for f in data["files"]}
    assert paths == {"ref1.md", "ref2.md"}


@pytest.mark.asyncio
async def test_skill_list_includes_file_count(client):
    skill_id = await _make_skill(client, "count-files-skill")
    await client.post(
        f"/api/v1/skills/{skill_id}/files",
        json={"path": "a.md", "content": "a"},
        headers=HEADERS,
    )
    r = await client.get("/api/v1/skills", headers=HEADERS)
    skills = r.json()["skills"]
    match = [s for s in skills if s["id"] == skill_id]
    assert len(match) == 1
    assert match[0]["file_count"] == 1


@pytest.mark.asyncio
async def test_cascade_delete_removes_files(client):
    skill_id = await _make_skill(client, "cascade-skill")
    await client.post(
        f"/api/v1/skills/{skill_id}/files",
        json={"path": "cascade.md", "content": "will be deleted"},
        headers=HEADERS,
    )
    await client.delete(f"/api/v1/skills/{skill_id}", headers=HEADERS)
    # After skill delete, files endpoint should 404
    r = await client.get(f"/api/v1/skills/{skill_id}/files", headers=HEADERS)
    assert r.status_code == 404


# --- Deploy folder ---


@pytest.mark.asyncio
async def test_deploy_folder(client):
    payload = {
        "name": "folder-skill",
        "content": "Main skill content",
        "description": "A folder skill",
        "files": [
            {"path": "references/guide.md", "content": "Guide text"},
            {"path": "references/examples.md", "content": "Example text here"},
        ],
    }
    r = await client.post("/api/v1/skills/deploy-folder", json=payload, headers=HEADERS)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "folder-skill"
    assert data["file_count"] == 2
    skill_id = data["id"]

    # Verify skill content
    r2 = await client.get(f"/api/v1/skills/{skill_id}", headers=HEADERS)
    assert r2.json()["content"] == "Main skill content"
    assert len(r2.json()["files"]) == 2

    # Verify file content is encrypted/decrypted properly
    file_id = r2.json()["files"][0]["id"]
    r3 = await client.get(f"/api/v1/skills/{skill_id}/files/{file_id}", headers=HEADERS)
    assert r3.status_code == 200
    assert r3.json()["content"] in ("Guide text", "Example text here")


# --- Ownership / scope tests ---

OTHER_HEADERS = {"Authorization": f"Bearer {OTHER_JWT}"}


@pytest.mark.asyncio
async def test_create_skill_captures_uploaded_by(client):
    r = await client.post(
        "/api/v1/skills",
        json={"name": "owned-skill", "content": "something"},
        headers=HEADERS,
    )
    assert r.status_code == 201
    skill_id = r.json()["id"]
    r2 = await client.get(f"/api/v1/skills/{skill_id}", headers=HEADERS)
    assert r2.status_code == 200
    assert r2.json()["uploaded_by"] == "test-user-id"


@pytest.mark.asyncio
async def test_personal_skill_only_visible_to_owner(client):
    r = await client.post(
        "/api/v1/skills",
        json={"name": "personal-skill", "content": "private", "scope": "personal"},
        headers=HEADERS,
    )
    assert r.status_code == 201
    skill_id = r.json()["id"]

    # User B cannot see it
    r_other_get = await client.get(f"/api/v1/skills/{skill_id}", headers=OTHER_HEADERS)
    assert r_other_get.status_code == 404

    r_other_list = await client.get("/api/v1/skills", headers=OTHER_HEADERS)
    other_ids = [s["id"] for s in r_other_list.json()["skills"]]
    assert skill_id not in other_ids

    # User A can see it
    r_owner_get = await client.get(f"/api/v1/skills/{skill_id}", headers=HEADERS)
    assert r_owner_get.status_code == 200

    r_owner_list = await client.get("/api/v1/skills", headers=HEADERS)
    owner_ids = [s["id"] for s in r_owner_list.json()["skills"]]
    assert skill_id in owner_ids


@pytest.mark.asyncio
async def test_personal_skill_not_in_employee_results(client):
    # Create a team
    db_r = await client.post("/api/v1/teams", json={"name": "emp-team"}, headers=HEADERS)
    assert db_r.status_code == 201
    team_id = db_r.json()["id"]
    team_token = db_r.json()["token"]

    # Create a personal skill
    ps_r = await client.post(
        "/api/v1/skills",
        json={"name": "personal-emp-skill", "content": "private", "scope": "personal"},
        headers=HEADERS,
    )
    assert ps_r.status_code == 201
    personal_skill_id = ps_r.json()["id"]

    # Assign it to the team
    await client.put(
        f"/api/v1/teams/{team_id}/skills",
        json={"skill_ids": [personal_skill_id]},
        headers=HEADERS,
    )

    # Employee endpoint should not return it (scope = personal)
    emp_r = await client.get(
        "/api/v1/employee/skills",
        headers={"X-Team-Token": team_token},
    )
    assert emp_r.status_code == 200
    emp_ids = [s["id"] for s in emp_r.json()["skills"]]
    assert personal_skill_id not in emp_ids


@pytest.mark.asyncio
async def test_team_to_personal_scope_change_blocked(client):
    r = await client.post(
        "/api/v1/skills",
        json={"name": "team-skill-noscope", "content": "content", "scope": "team"},
        headers=HEADERS,
    )
    assert r.status_code == 201
    skill_id = r.json()["id"]
    r2 = await client.put(
        f"/api/v1/skills/{skill_id}",
        json={"scope": "personal"},
        headers=HEADERS,
    )
    assert r2.status_code == 422


@pytest.mark.asyncio
async def test_personal_to_team_scope_change_allowed(client):
    r = await client.post(
        "/api/v1/skills",
        json={"name": "personal-to-team-skill", "content": "content", "scope": "personal"},
        headers=HEADERS,
    )
    assert r.status_code == 201
    skill_id = r.json()["id"]
    r2 = await client.put(
        f"/api/v1/skills/{skill_id}",
        json={"scope": "team"},
        headers=HEADERS,
    )
    assert r2.status_code == 200
    assert r2.json()["scope"] == "team"


@pytest.mark.asyncio
async def test_non_owner_cannot_delete_personal_skill(client):
    r = await client.post(
        "/api/v1/skills",
        json={"name": "personal-del-skill", "content": "mine", "scope": "personal"},
        headers=HEADERS,
    )
    assert r.status_code == 201
    skill_id = r.json()["id"]
    r2 = await client.delete(f"/api/v1/skills/{skill_id}", headers=OTHER_HEADERS)
    assert r2.status_code == 403


@pytest.mark.asyncio
async def test_bundle_excludes_personal_skills(client):
    # Create a personal skill
    r_personal = await client.post(
        "/api/v1/skills",
        json={"name": "bundle-personal-skill", "content": "private content", "scope": "personal"},
        headers=HEADERS,
    )
    assert r_personal.status_code == 201
    personal_id = r_personal.json()["id"]

    # Create a team skill
    r_team = await client.post(
        "/api/v1/skills",
        json={"name": "bundle-team-skill", "content": "team content", "scope": "team"},
        headers=HEADERS,
    )
    assert r_team.status_code == 201
    team_id = r_team.json()["id"]

    r_bundle = await client.get("/api/v1/skills/bundle", headers=HEADERS)
    assert r_bundle.status_code == 200
    bundle_ids = [s["id"] for s in r_bundle.json()["skills"]]
    assert team_id in bundle_ids
    assert personal_id not in bundle_ids
