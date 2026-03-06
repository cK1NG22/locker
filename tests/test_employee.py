import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from tests.conftest import TEST_JWT

from main import app
from vault.db import init_db, close_db

ADMIN = {"Authorization": f"Bearer {TEST_JWT}"}


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
        json={"name": "legal-brief", "content": "secret", "description": "Generates legal briefs", "visibility": "shared"},
        headers=ADMIN,
    )
    s2 = await client.post(
        "/api/v1/skills",
        json={"name": "contract-review", "content": "secret2", "visibility": "shared"},
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
        assert skill.get("content") is None


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


@pytest.mark.asyncio
async def test_visibility_hidden_skill_not_returned(client):
    skill = await client.post(
        "/api/v1/skills",
        json={"name": "secret-skill", "content": "top secret", "visibility": "hidden"},
        headers=ADMIN,
    )
    team = await client.post("/api/v1/teams", json={"name": "T1"}, headers=ADMIN)
    team_data = team.json()
    await client.put(
        f"/api/v1/teams/{team_data['id']}/skills",
        json={"skill_ids": [skill.json()["id"]]},
        headers=ADMIN,
    )
    r = await client.get("/api/v1/employee/skills", headers={"X-Team-Token": team_data["token"]})
    assert r.status_code == 200
    names = [s["name"] for s in r.json()["skills"]]
    assert "secret-skill" not in names


@pytest.mark.asyncio
async def test_visibility_shared_skill_no_content(client):
    skill = await client.post(
        "/api/v1/skills",
        json={"name": "shared-skill", "content": "the prompt", "description": "A shared skill", "visibility": "shared"},
        headers=ADMIN,
    )
    team = await client.post("/api/v1/teams", json={"name": "T2"}, headers=ADMIN)
    team_data = team.json()
    await client.put(
        f"/api/v1/teams/{team_data['id']}/skills",
        json={"skill_ids": [skill.json()["id"]]},
        headers=ADMIN,
    )
    r = await client.get("/api/v1/employee/skills", headers={"X-Team-Token": team_data["token"]})
    assert r.status_code == 200
    skills = {s["name"]: s for s in r.json()["skills"]}
    assert "shared-skill" in skills
    assert skills["shared-skill"]["description"] == "A shared skill"
    assert skills["shared-skill"]["content"] is None


@pytest.mark.asyncio
async def test_visibility_open_skill_has_content(client):
    skill = await client.post(
        "/api/v1/skills",
        json={"name": "open-skill", "content": "the full prompt", "description": "An open skill", "visibility": "open"},
        headers=ADMIN,
    )
    team = await client.post("/api/v1/teams", json={"name": "T3"}, headers=ADMIN)
    team_data = team.json()
    await client.put(
        f"/api/v1/teams/{team_data['id']}/skills",
        json={"skill_ids": [skill.json()["id"]]},
        headers=ADMIN,
    )
    r = await client.get("/api/v1/employee/skills", headers={"X-Team-Token": team_data["token"]})
    assert r.status_code == 200
    skills = {s["name"]: s for s in r.json()["skills"]}
    assert "open-skill" in skills
    assert skills["open-skill"]["description"] == "An open skill"
    assert skills["open-skill"]["content"] == "the full prompt"
