import base64
import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Generate test keys before app is imported
TEST_API_KEY = "test-api-key-1234"
TEST_ENC_KEY = base64.b64encode(AESGCM.generate_key(256)).decode()

os.environ["LOCKER_API_KEY"] = TEST_API_KEY
os.environ["LOCKER_ENCRYPTION_KEY"] = TEST_ENC_KEY
os.environ["LOCKER_DB_PATH"] = ":memory:"

from main import app  # noqa: E402
from vault.db import init_db, close_db  # noqa: E402

HEADERS = {"X-API-Key": TEST_API_KEY}
BAD_HEADERS = {"X-API-Key": "wrong-key"}


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
async def test_no_api_key_returns_401(client):
    r = await client.get("/api/v1/skills")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_wrong_api_key_returns_401(client):
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
    assert "created_at" in data
    assert "content" not in data


@pytest.mark.asyncio
async def test_create_duplicate_name_returns_409(client):
    payload = {"name": "dup-skill", "content": "original"}
    await client.post("/api/v1/skills", json=payload, headers=HEADERS)
    r = await client.post("/api/v1/skills", json=payload, headers=HEADERS)
    assert r.status_code == 409


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


@pytest.mark.asyncio
async def test_deploy_folder_duplicate_name_returns_409(client):
    payload = {"name": "dup-folder", "content": "content", "files": []}
    await client.post("/api/v1/skills/deploy-folder", json=payload, headers=HEADERS)
    r = await client.post("/api/v1/skills/deploy-folder", json=payload, headers=HEADERS)
    assert r.status_code == 409
