import base64
import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

TEST_API_KEY = "test-api-key-1234"
TEST_ENC_KEY = base64.b64encode(AESGCM.generate_key(256)).decode()

os.environ["LOCKER_API_KEY"] = TEST_API_KEY
os.environ["LOCKER_ENCRYPTION_KEY"] = TEST_ENC_KEY
os.environ["LOCKER_DB_PATH"] = ":memory:"

from main import app  # noqa: E402
from vault.db import init_db, close_db  # noqa: E402

ADMIN = {"X-API-Key": TEST_API_KEY}


@pytest_asyncio.fixture
async def client():
    await init_db()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
    await close_db()


async def _setup_team_with_skills(client):
    """Create a team with 2 skills (one with description, one without) and return team token."""
    s1 = await client.post(
        "/api/v1/skills",
        json={"name": "legal-brief", "content": "secret", "description": "Generates legal briefs"},
        headers=ADMIN,
    )
    s2 = await client.post(
        "/api/v1/skills",
        json={"name": "contract-review", "content": "secret2"},
        headers=ADMIN,
    )
    team = await client.post(
        "/api/v1/teams", json={"name": "Legal"}, headers=ADMIN
    )
    team_data = team.json()
    await client.put(
        f"/api/v1/teams/{team_data['id']}/skills",
        json={"skill_ids": [s1.json()["id"], s2.json()["id"]]},
        headers=ADMIN,
    )
    return team_data["token"]


@pytest.mark.asyncio
async def test_employee_skills_returns_list(client):
    token = await _setup_team_with_skills(client)
    r = await client.get(
        "/api/v1/employee/skills", headers={"X-Team-Token": token}
    )
    assert r.status_code == 200
    data = r.json()
    assert data["team"] == "Legal"
    names = [s["name"] for s in data["skills"]]
    assert "legal-brief" in names
    assert "contract-review" in names


@pytest.mark.asyncio
async def test_employee_skills_includes_description(client):
    token = await _setup_team_with_skills(client)
    r = await client.get(
        "/api/v1/employee/skills", headers={"X-Team-Token": token}
    )
    skills = {s["name"]: s for s in r.json()["skills"]}
    assert skills["legal-brief"]["description"] == "Generates legal briefs"
    assert skills["contract-review"]["description"] is None


@pytest.mark.asyncio
async def test_employee_skills_no_content_returned(client):
    token = await _setup_team_with_skills(client)
    r = await client.get(
        "/api/v1/employee/skills", headers={"X-Team-Token": token}
    )
    for skill in r.json()["skills"]:
        assert "content" not in skill


@pytest.mark.asyncio
async def test_employee_skills_no_token_returns_401(client):
    r = await client.get("/api/v1/employee/skills")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_employee_skills_bad_token_returns_401(client):
    r = await client.get(
        "/api/v1/employee/skills", headers={"X-Team-Token": "invalid-token"}
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_employee_skills_empty_team(client):
    team = await client.post(
        "/api/v1/teams", json={"name": "Empty Team"}, headers=ADMIN
    )
    token = team.json()["token"]
    r = await client.get(
        "/api/v1/employee/skills", headers={"X-Team-Token": token}
    )
    assert r.status_code == 200
    assert r.json()["skills"] == []


@pytest.mark.asyncio
async def test_employee_no_admin_key_needed(client):
    """Employee endpoint should NOT require X-API-Key."""
    token = await _setup_team_with_skills(client)
    r = await client.get(
        "/api/v1/employee/skills", headers={"X-Team-Token": token}
    )
    assert r.status_code == 200
