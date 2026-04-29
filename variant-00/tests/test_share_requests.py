import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from tests.conftest import TEST_JWT, OTHER_JWT

from main import app
from vault.db import init_db, close_db

HEADERS = {"Authorization": f"Bearer {TEST_JWT}"}
OTHER_HEADERS = {"Authorization": f"Bearer {OTHER_JWT}"}


@pytest_asyncio.fixture
async def client():
    await init_db()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
    await close_db()


async def _seed_users():
    from vault.db import get_db
    db = get_db()
    await db.execute(
        "INSERT INTO users (id, email, name, google_id, created_at) VALUES ($1, $2, $3, $4, $5) ON CONFLICT DO NOTHING",
        "test-user-id", "test@example.com", "Test User", "google-test", "2026-01-01T00:00:00",
    )
    await db.execute(
        "INSERT INTO users (id, email, name, google_id, created_at) VALUES ($1, $2, $3, $4, $5) ON CONFLICT DO NOTHING",
        "other-user-id", "other@example.com", "Other User", "google-other", "2026-01-01T00:00:00",
    )


async def _setup_org_with_two_teams(client):
    """Create org, two teams, link them, create a skill, assign to team1."""
    await _seed_users()
    org_r = await client.post("/api/v1/orgs", json={"name": "Share Org", "slug": "share-org"}, headers=HEADERS)
    org = org_r.json()
    t1_r = await client.post("/api/v1/teams", json={"name": "Team Alpha"}, headers=HEADERS)
    team1 = t1_r.json()
    t2_r = await client.post("/api/v1/teams", json={"name": "Team Beta"}, headers=HEADERS)
    team2 = t2_r.json()
    await client.post(f"/api/v1/orgs/{org['id']}/teams/{team1['id']}", headers=HEADERS)
    await client.post(f"/api/v1/orgs/{org['id']}/teams/{team2['id']}", headers=HEADERS)
    # Create and assign skill to team1
    skill_r = await client.post("/api/v1/skills", json={"name": "shared-skill", "content": "skill content"}, headers=HEADERS)
    skill = skill_r.json()
    await client.put(f"/api/v1/teams/{team1['id']}/skills", json={"skill_ids": [skill["id"]]}, headers=HEADERS)
    return org, team1, team2, skill


@pytest.mark.asyncio
async def test_create_share_request(client):
    org, team1, team2, skill = await _setup_org_with_two_teams(client)
    r = await client.post(
        "/api/v1/share-requests",
        json={"skill_id": skill["id"], "from_team_id": team1["id"], "to_team_id": team2["id"]},
        headers=HEADERS,
    )
    assert r.status_code == 201
    assert r.json()["status"] == "pending"


@pytest.mark.asyncio
async def test_share_request_requires_same_org(client):
    await _seed_users()
    org1_r = await client.post("/api/v1/orgs", json={"name": "Org 1", "slug": "org-1"}, headers=HEADERS)
    org2_r = await client.post("/api/v1/orgs", json={"name": "Org 2", "slug": "org-2"}, headers=HEADERS)
    t1_r = await client.post("/api/v1/teams", json={"name": "Org1 Team"}, headers=HEADERS)
    t2_r = await client.post("/api/v1/teams", json={"name": "Org2 Team"}, headers=HEADERS)
    await client.post(f"/api/v1/orgs/{org1_r.json()['id']}/teams/{t1_r.json()['id']}", headers=HEADERS)
    await client.post(f"/api/v1/orgs/{org2_r.json()['id']}/teams/{t2_r.json()['id']}", headers=HEADERS)
    skill_r = await client.post("/api/v1/skills", json={"name": "cross-org-skill", "content": "c"}, headers=HEADERS)
    await client.put(f"/api/v1/teams/{t1_r.json()['id']}/skills", json={"skill_ids": [skill_r.json()["id"]]}, headers=HEADERS)
    r = await client.post(
        "/api/v1/share-requests",
        json={"skill_id": skill_r.json()["id"], "from_team_id": t1_r.json()["id"], "to_team_id": t2_r.json()["id"]},
        headers=HEADERS,
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_approve_share_request_links_skill(client):
    org, team1, team2, skill = await _setup_org_with_two_teams(client)
    create_r = await client.post(
        "/api/v1/share-requests",
        json={"skill_id": skill["id"], "from_team_id": team1["id"], "to_team_id": team2["id"]},
        headers=HEADERS,
    )
    req_id = create_r.json()["id"]
    r = await client.patch(
        f"/api/v1/share-requests/{req_id}",
        json={"status": "approved"},
        headers=HEADERS,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "approved"
    # Verify skill is now in team2
    detail = await client.get(f"/api/v1/teams/{team2['id']}", headers=HEADERS)
    assert "shared-skill" in detail.json()["skills"]


@pytest.mark.asyncio
async def test_deny_share_request(client):
    org, team1, team2, skill = await _setup_org_with_two_teams(client)
    create_r = await client.post(
        "/api/v1/share-requests",
        json={"skill_id": skill["id"], "from_team_id": team1["id"], "to_team_id": team2["id"]},
        headers=HEADERS,
    )
    req_id = create_r.json()["id"]
    r = await client.patch(
        f"/api/v1/share-requests/{req_id}",
        json={"status": "denied"},
        headers=HEADERS,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "denied"
    # Verify skill is NOT in team2
    detail = await client.get(f"/api/v1/teams/{team2['id']}", headers=HEADERS)
    assert "shared-skill" not in detail.json()["skills"]


@pytest.mark.asyncio
async def test_cannot_resolve_already_resolved(client):
    org, team1, team2, skill = await _setup_org_with_two_teams(client)
    create_r = await client.post(
        "/api/v1/share-requests",
        json={"skill_id": skill["id"], "from_team_id": team1["id"], "to_team_id": team2["id"]},
        headers=HEADERS,
    )
    req_id = create_r.json()["id"]
    await client.patch(f"/api/v1/share-requests/{req_id}", json={"status": "approved"}, headers=HEADERS)
    r = await client.patch(f"/api/v1/share-requests/{req_id}", json={"status": "denied"}, headers=HEADERS)
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_list_pending_share_requests(client):
    org, team1, team2, skill = await _setup_org_with_two_teams(client)
    await client.post(
        "/api/v1/share-requests",
        json={"skill_id": skill["id"], "from_team_id": team1["id"], "to_team_id": team2["id"]},
        headers=HEADERS,
    )
    r = await client.get(f"/api/v1/share-requests?team_id={team2['id']}", headers=HEADERS)
    assert r.status_code == 200
    assert len(r.json()["requests"]) == 1
    assert r.json()["requests"][0]["status"] == "pending"
