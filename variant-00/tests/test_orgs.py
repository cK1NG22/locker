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


async def _seed_users(client):
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


async def _create_org(client, name="Test Org", slug="test-org"):
    r = await client.post("/api/v1/orgs", json={"name": name, "slug": slug}, headers=HEADERS)
    assert r.status_code == 201
    return r.json()


async def _create_team(client, name="Test Team"):
    r = await client.post("/api/v1/teams", json={"name": name}, headers=HEADERS)
    assert r.status_code == 201
    return r.json()


# --- Auth ---


@pytest.mark.asyncio
async def test_orgs_require_auth(client):
    r = await client.get("/api/v1/orgs")
    assert r.status_code == 401


# --- Create ---


@pytest.mark.asyncio
async def test_create_org(client):
    r = await client.post(
        "/api/v1/orgs", json={"name": "Acme Corp", "slug": "acme-corp"}, headers=HEADERS
    )
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Acme Corp"
    assert data["slug"] == "acme-corp"
    assert data["owner_id"] == "test-user-id"
    assert data["skill_convention"] == "/l"


@pytest.mark.asyncio
async def test_create_org_invalid_slug(client):
    r = await client.post(
        "/api/v1/orgs", json={"name": "Bad", "slug": "AB!"}, headers=HEADERS
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_create_org_duplicate_slug(client):
    await _create_org(client, "Org A", "dup-slug")
    r = await client.post(
        "/api/v1/orgs", json={"name": "Org B", "slug": "dup-slug"}, headers=HEADERS
    )
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_create_org_auto_adds_creator_as_admin(client):
    org = await _create_org(client)
    r = await client.get(f"/api/v1/orgs/{org['id']}", headers=HEADERS)
    members = r.json()["members"]
    assert len(members) == 1
    assert members[0]["user_id"] == "test-user-id"
    assert members[0]["role"] == "org_admin"


# --- List ---


@pytest.mark.asyncio
async def test_list_orgs_scoped_to_user(client):
    await _create_org(client, "My Org", "my-org")
    r = await client.get("/api/v1/orgs", headers=HEADERS)
    assert r.status_code == 200
    assert len(r.json()) == 1
    # Other user sees none
    r2 = await client.get("/api/v1/orgs", headers=OTHER_HEADERS)
    assert r2.status_code == 200
    assert len(r2.json()) == 0


# --- Get ---


@pytest.mark.asyncio
async def test_get_org_detail(client):
    org = await _create_org(client)
    r = await client.get(f"/api/v1/orgs/{org['id']}", headers=HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Test Org"
    assert "teams" in data
    assert "members" in data


@pytest.mark.asyncio
async def test_get_org_non_member_forbidden(client):
    org = await _create_org(client)
    r = await client.get(f"/api/v1/orgs/{org['id']}", headers=OTHER_HEADERS)
    assert r.status_code == 403


# --- Update ---


@pytest.mark.asyncio
async def test_update_org(client):
    org = await _create_org(client)
    r = await client.put(
        f"/api/v1/orgs/{org['id']}",
        json={"name": "Renamed", "skill_convention": "/locker"},
        headers=HEADERS,
    )
    assert r.status_code == 200
    assert r.json()["name"] == "Renamed"
    assert r.json()["skill_convention"] == "/locker"


@pytest.mark.asyncio
async def test_update_org_non_admin_forbidden(client):
    org = await _create_org(client)
    r = await client.put(
        f"/api/v1/orgs/{org['id']}", json={"name": "Nope"}, headers=OTHER_HEADERS
    )
    assert r.status_code == 403


# --- Delete ---


@pytest.mark.asyncio
async def test_delete_org(client):
    org = await _create_org(client)
    r = await client.delete(f"/api/v1/orgs/{org['id']}", headers=HEADERS)
    assert r.status_code == 204
    r2 = await client.get("/api/v1/orgs", headers=HEADERS)
    assert len(r2.json()) == 0


@pytest.mark.asyncio
async def test_delete_org_non_owner_forbidden(client):
    org = await _create_org(client)
    r = await client.delete(f"/api/v1/orgs/{org['id']}", headers=OTHER_HEADERS)
    assert r.status_code == 403


# --- Member management ---


@pytest.mark.asyncio
async def test_add_org_member(client):
    await _seed_users(client)
    org = await _create_org(client)
    r = await client.post(
        f"/api/v1/orgs/{org['id']}/members",
        json={"email": "other@example.com"},
        headers=HEADERS,
    )
    assert r.status_code == 201
    assert r.json()["role"] == "member"
    assert r.json()["email"] == "other@example.com"


@pytest.mark.asyncio
async def test_add_duplicate_org_member(client):
    await _seed_users(client)
    org = await _create_org(client)
    await client.post(
        f"/api/v1/orgs/{org['id']}/members",
        json={"email": "other@example.com"},
        headers=HEADERS,
    )
    r = await client.post(
        f"/api/v1/orgs/{org['id']}/members",
        json={"email": "other@example.com"},
        headers=HEADERS,
    )
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_remove_org_member(client):
    await _seed_users(client)
    org = await _create_org(client)
    add_r = await client.post(
        f"/api/v1/orgs/{org['id']}/members",
        json={"email": "other@example.com"},
        headers=HEADERS,
    )
    member_id = add_r.json()["id"]
    r = await client.delete(f"/api/v1/orgs/{org['id']}/members/{member_id}", headers=HEADERS)
    assert r.status_code == 204


@pytest.mark.asyncio
async def test_cannot_remove_org_owner(client):
    await _seed_users(client)
    org = await _create_org(client)
    detail = await client.get(f"/api/v1/orgs/{org['id']}", headers=HEADERS)
    owner_member_id = detail.json()["members"][0]["id"]
    r = await client.delete(f"/api/v1/orgs/{org['id']}/members/{owner_member_id}", headers=HEADERS)
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_update_org_member_role(client):
    await _seed_users(client)
    org = await _create_org(client)
    add_r = await client.post(
        f"/api/v1/orgs/{org['id']}/members",
        json={"email": "other@example.com"},
        headers=HEADERS,
    )
    member_id = add_r.json()["id"]
    r = await client.patch(
        f"/api/v1/orgs/{org['id']}/members/{member_id}",
        json={"role": "org_admin"},
        headers=HEADERS,
    )
    assert r.status_code == 200
    assert r.json()["role"] == "org_admin"


# --- Team linking ---


@pytest.mark.asyncio
async def test_link_team_to_org(client):
    org = await _create_org(client)
    team = await _create_team(client, "Linked Team")
    r = await client.post(f"/api/v1/orgs/{org['id']}/teams/{team['id']}", headers=HEADERS)
    assert r.status_code == 200
    # Verify team appears in org detail
    detail = await client.get(f"/api/v1/orgs/{org['id']}", headers=HEADERS)
    team_names = [t["name"] for t in detail.json()["teams"]]
    assert "Linked Team" in team_names


@pytest.mark.asyncio
async def test_unlink_team_from_org(client):
    org = await _create_org(client)
    team = await _create_team(client, "Unlink Team")
    await client.post(f"/api/v1/orgs/{org['id']}/teams/{team['id']}", headers=HEADERS)
    r = await client.delete(f"/api/v1/orgs/{org['id']}/teams/{team['id']}", headers=HEADERS)
    assert r.status_code == 200
    detail = await client.get(f"/api/v1/orgs/{org['id']}", headers=HEADERS)
    assert len(detail.json()["teams"]) == 0


@pytest.mark.asyncio
async def test_link_team_already_in_another_org(client):
    org1 = await _create_org(client, "Org 1", "org-1")
    org2 = await _create_org(client, "Org 2", "org-2")
    team = await _create_team(client, "Contested Team")
    await client.post(f"/api/v1/orgs/{org1['id']}/teams/{team['id']}", headers=HEADERS)
    r = await client.post(f"/api/v1/orgs/{org2['id']}/teams/{team['id']}", headers=HEADERS)
    assert r.status_code == 409


# --- list_teams scoping bug fix ---


@pytest.mark.asyncio
async def test_list_teams_scoped_to_user_membership(client):
    """list_teams should only return teams the user belongs to (or via org membership)."""
    await _seed_users(client)
    await _create_team(client, "User Team")
    # Other user should not see this team
    r = await client.get("/api/v1/teams", headers=OTHER_HEADERS)
    assert r.status_code == 200
    names = [t["name"] for t in r.json()]
    assert "User Team" not in names


# --- Analytics ---


@pytest.mark.asyncio
async def test_org_skills_aggregates_across_teams(client):
    org = await _create_org(client)
    team = await _create_team(client, "Analytics Team")
    await client.post(f"/api/v1/orgs/{org['id']}/teams/{team['id']}", headers=HEADERS)
    # Create and assign a skill
    sr = await client.post("/api/v1/skills", json={"name": "analytics-skill", "content": "c"}, headers=HEADERS)
    skill = sr.json()
    await client.put(f"/api/v1/teams/{team['id']}/skills", json={"skill_ids": [skill["id"]]}, headers=HEADERS)
    r = await client.get(f"/api/v1/orgs/{org['id']}/skills", headers=HEADERS)
    assert r.status_code == 200
    assert len(r.json()["skills"]) == 1
    assert r.json()["skills"][0]["name"] == "analytics-skill"


@pytest.mark.asyncio
async def test_org_skills_non_admin_forbidden(client):
    org = await _create_org(client)
    r = await client.get(f"/api/v1/orgs/{org['id']}/skills", headers=OTHER_HEADERS)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_org_usage_summary(client):
    org = await _create_org(client)
    team = await _create_team(client, "Usage Team")
    await client.post(f"/api/v1/orgs/{org['id']}/teams/{team['id']}", headers=HEADERS)
    # Insert usage records directly
    from vault.db import get_db
    import uuid
    db = get_db()
    for _ in range(3):
        await db.execute(
            "INSERT INTO skill_usage (id, skill_name, team_id, invoked_at, source) VALUES ($1, $2, $3, $4, $5)",
            str(uuid.uuid4()), "test-skill", team["id"], "2026-03-07T00:00:00", "mcp",
        )
    r = await client.get(f"/api/v1/orgs/{org['id']}/usage/summary", headers=HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert data["by_skill"][0]["skill_name"] == "test-skill"
    assert data["by_skill"][0]["count"] == 3
    assert data["by_team"][0]["team_name"] == "Usage Team"


@pytest.mark.asyncio
async def test_list_teams_includes_org_teams(client):
    """Teams linked to user's org should appear in list_teams."""
    await _seed_users(client)
    org = await _create_org(client)
    team = await _create_team(client, "Org Team")
    await client.post(f"/api/v1/orgs/{org['id']}/teams/{team['id']}", headers=HEADERS)
    # Add other user to org
    await client.post(
        f"/api/v1/orgs/{org['id']}/members",
        json={"email": "other@example.com"},
        headers=HEADERS,
    )
    # Other user should see the org's team
    r = await client.get("/api/v1/teams", headers=OTHER_HEADERS)
    names = [t["name"] for t in r.json()]
    assert "Org Team" in names
