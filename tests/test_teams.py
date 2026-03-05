import base64
import os
from datetime import datetime, timezone

import jwt as _jwt
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

TEST_JWT_SECRET = "test-jwt-secret"
TEST_ENC_KEY = base64.b64encode(AESGCM.generate_key(256)).decode()

os.environ["LOCKER_JWT_SECRET"] = TEST_JWT_SECRET
os.environ["LOCKER_ENCRYPTION_KEY"] = TEST_ENC_KEY
os.environ["LOCKER_DB_PATH"] = ":memory:"

_TEST_PAYLOAD = {
    "sub": "test-user-id",
    "email": "test@example.com",
    "exp": datetime(2099, 1, 1, tzinfo=timezone.utc),
}
TEST_JWT = _jwt.encode(_TEST_PAYLOAD, TEST_JWT_SECRET, algorithm="HS256")

from main import app  # noqa: E402
from vault.db import init_db, close_db  # noqa: E402

HEADERS = {"Authorization": f"Bearer {TEST_JWT}"}


@pytest_asyncio.fixture
async def client():
    await init_db()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
    await close_db()


async def _create_skill(client, name="test-skill", description=None):
    payload = {"name": name, "content": "skill content"}
    if description:
        payload["description"] = description
    r = await client.post("/api/v1/skills", json=payload, headers=HEADERS)
    return r.json()


async def _create_team(client, name="Legal"):
    r = await client.post("/api/v1/teams", json={"name": name}, headers=HEADERS)
    return r.json()


# --- Auth ---


@pytest.mark.asyncio
async def test_teams_require_auth(client):
    r = await client.get("/api/v1/teams")
    assert r.status_code == 401


# --- Create ---


@pytest.mark.asyncio
async def test_create_team(client):
    r = await client.post(
        "/api/v1/teams", json={"name": "Engineering"}, headers=HEADERS
    )
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Engineering"
    assert "id" in data
    assert "token" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_duplicate_team_returns_409(client):
    await _create_team(client, "Dup Team")
    r = await client.post(
        "/api/v1/teams", json={"name": "Dup Team"}, headers=HEADERS
    )
    assert r.status_code == 409


# --- List ---


@pytest.mark.asyncio
async def test_list_teams(client):
    await _create_team(client, "Team A")
    await _create_team(client, "Team B")
    r = await client.get("/api/v1/teams", headers=HEADERS)
    assert r.status_code == 200
    teams = r.json()
    names = [t["name"] for t in teams]
    assert "Team A" in names
    assert "Team B" in names
    assert all("skill_count" in t for t in teams)


# --- Get ---


@pytest.mark.asyncio
async def test_get_team(client):
    team = await _create_team(client, "Detail Team")
    r = await client.get(f"/api/v1/teams/{team['id']}", headers=HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Detail Team"
    assert data["skills"] == []


@pytest.mark.asyncio
async def test_get_missing_team_returns_404(client):
    r = await client.get("/api/v1/teams/nonexistent", headers=HEADERS)
    assert r.status_code == 404


# --- Update ---


@pytest.mark.asyncio
async def test_rename_team(client):
    team = await _create_team(client, "Old Name")
    r = await client.put(
        f"/api/v1/teams/{team['id']}",
        json={"name": "New Name"},
        headers=HEADERS,
    )
    assert r.status_code == 200
    assert r.json()["name"] == "New Name"


@pytest.mark.asyncio
async def test_rename_missing_team_returns_404(client):
    r = await client.put(
        "/api/v1/teams/nonexistent",
        json={"name": "Nope"},
        headers=HEADERS,
    )
    assert r.status_code == 404


# --- Delete ---


@pytest.mark.asyncio
async def test_delete_team(client):
    team = await _create_team(client, "Delete Me")
    r = await client.delete(f"/api/v1/teams/{team['id']}", headers=HEADERS)
    assert r.status_code == 204
    r2 = await client.get(f"/api/v1/teams/{team['id']}", headers=HEADERS)
    assert r2.status_code == 404


@pytest.mark.asyncio
async def test_delete_missing_team_returns_404(client):
    r = await client.delete("/api/v1/teams/nonexistent", headers=HEADERS)
    assert r.status_code == 404


# --- Skill Assignment ---


@pytest.mark.asyncio
async def test_set_team_skills(client):
    team = await _create_team(client, "Assign Team")
    skill1 = await _create_skill(client, "skill-a")
    skill2 = await _create_skill(client, "skill-b")
    r = await client.put(
        f"/api/v1/teams/{team['id']}/skills",
        json={"skill_ids": [skill1["id"], skill2["id"]]},
        headers=HEADERS,
    )
    assert r.status_code == 200
    # Verify via get team detail
    detail = await client.get(f"/api/v1/teams/{team['id']}", headers=HEADERS)
    assert set(detail.json()["skills"]) == {"skill-a", "skill-b"}


@pytest.mark.asyncio
async def test_set_team_skills_replaces(client):
    team = await _create_team(client, "Replace Team")
    skill1 = await _create_skill(client, "skill-x")
    skill2 = await _create_skill(client, "skill-y")
    await client.put(
        f"/api/v1/teams/{team['id']}/skills",
        json={"skill_ids": [skill1["id"], skill2["id"]]},
        headers=HEADERS,
    )
    # Replace with only skill2
    await client.put(
        f"/api/v1/teams/{team['id']}/skills",
        json={"skill_ids": [skill2["id"]]},
        headers=HEADERS,
    )
    detail = await client.get(f"/api/v1/teams/{team['id']}", headers=HEADERS)
    assert detail.json()["skills"] == ["skill-y"]


@pytest.mark.asyncio
async def test_set_skills_invalid_skill_returns_404(client):
    team = await _create_team(client, "Bad Assign")
    r = await client.put(
        f"/api/v1/teams/{team['id']}/skills",
        json={"skill_ids": ["nonexistent"]},
        headers=HEADERS,
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_set_skills_missing_team_returns_404(client):
    r = await client.put(
        "/api/v1/teams/nonexistent/skills",
        json={"skill_ids": []},
        headers=HEADERS,
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_list_teams_shows_skill_count(client):
    team = await _create_team(client, "Count Team")
    skill = await _create_skill(client, "count-skill")
    await client.put(
        f"/api/v1/teams/{team['id']}/skills",
        json={"skill_ids": [skill["id"]]},
        headers=HEADERS,
    )
    r = await client.get("/api/v1/teams", headers=HEADERS)
    matching = [t for t in r.json() if t["name"] == "Count Team"]
    assert matching[0]["skill_count"] == 1


@pytest.mark.asyncio
async def test_delete_team_cascades_skill_assignments(client):
    team = await _create_team(client, "Cascade Team")
    skill = await _create_skill(client, "cascade-skill")
    await client.put(
        f"/api/v1/teams/{team['id']}/skills",
        json={"skill_ids": [skill["id"]]},
        headers=HEADERS,
    )
    await client.delete(f"/api/v1/teams/{team['id']}", headers=HEADERS)
    # Team gone — skill should still exist
    r = await client.get(f"/api/v1/skills/{skill['id']}", headers=HEADERS)
    assert r.status_code == 200
