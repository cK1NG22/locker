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


# --- Ownership ---


@pytest.mark.asyncio
async def test_create_team_sets_owner_id(client):
    r = await client.post("/api/v1/teams", json={"name": "Owned Team"}, headers=HEADERS)
    assert r.status_code == 201
    data = r.json()
    assert data["owner_id"] == "test-user-id"


@pytest.mark.asyncio
async def test_create_team_auto_adds_creator_as_admin_member(client):
    r = await client.post("/api/v1/teams", json={"name": "Member Team"}, headers=HEADERS)
    team_id = r.json()["id"]
    detail = await client.get(f"/api/v1/teams/{team_id}", headers=HEADERS)
    members = detail.json()["members"]
    assert len(members) == 1
    assert members[0]["user_id"] == "test-user-id"
    assert members[0]["role"] == "admin"
    assert members[0]["can_share"] is True


@pytest.mark.asyncio
async def test_get_team_includes_members(client):
    r = await client.post("/api/v1/teams", json={"name": "Members Detail Team"}, headers=HEADERS)
    team_id = r.json()["id"]
    detail = await client.get(f"/api/v1/teams/{team_id}", headers=HEADERS)
    data = detail.json()
    assert "members" in data
    assert isinstance(data["members"], list)


@pytest.mark.asyncio
async def test_non_admin_cannot_rename_team(client):
    team = await _create_team(client, "Protected Team")
    r = await client.put(
        f"/api/v1/teams/{team['id']}",
        json={"name": "Hijacked"},
        headers=OTHER_HEADERS,
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_non_admin_cannot_delete_team(client):
    team = await _create_team(client, "No Delete Team")
    r = await client.delete(f"/api/v1/teams/{team['id']}", headers=OTHER_HEADERS)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_non_admin_cannot_set_team_skills(client):
    team = await _create_team(client, "No Skills Team")
    skill = await _create_skill(client, "protected-skill")
    r = await client.put(
        f"/api/v1/teams/{team['id']}/skills",
        json={"skill_ids": [skill["id"]]},
        headers=OTHER_HEADERS,
    )
    assert r.status_code == 403


# --- can_share permissions ---


async def _add_other_user_to_db(client):
    """Insert the 'other' test user into the users table so add_member can find them."""
    from vault.db import get_db
    db = get_db()
    await db.execute(
        "INSERT INTO users (id, email, name, google_id, created_at) VALUES ($1, $2, $3, $4, $5) ON CONFLICT DO NOTHING",
        "other-user-id", "other@example.com", "Other User", "google-other", "2026-01-01T00:00:00",
    )
    await db.execute(
        "INSERT INTO users (id, email, name, google_id, created_at) VALUES ($1, $2, $3, $4, $5) ON CONFLICT DO NOTHING",
        "test-user-id", "test@example.com", "Test User", "google-test", "2026-01-01T00:00:00",
    )


async def _add_member_to_team(client, team_id, can_share=False):
    """Add 'other' user to a team via the API and return the member."""
    await _add_other_user_to_db(client)
    r = await client.post(
        f"/api/v1/teams/{team_id}/members",
        json={"email": "other@example.com"},
        headers=HEADERS,
    )
    assert r.status_code == 201
    member = r.json()
    if can_share:
        await client.patch(
            f"/api/v1/teams/{team_id}/members/{member['id']}",
            json={"can_share": True},
            headers=HEADERS,
        )
    return member


@pytest.mark.asyncio
async def test_member_with_can_share_can_assign_skills(client):
    team = await _create_team(client, "Share Team")
    skill = await _create_skill(client, "share-skill")
    await _add_member_to_team(client, team["id"], can_share=True)
    r = await client.put(
        f"/api/v1/teams/{team['id']}/skills",
        json={"skill_ids": [skill["id"]]},
        headers=OTHER_HEADERS,
    )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_member_without_can_share_cannot_assign_skills(client):
    team = await _create_team(client, "No Share Team")
    skill = await _create_skill(client, "noshare-skill")
    await _add_member_to_team(client, team["id"], can_share=False)
    r = await client.put(
        f"/api/v1/teams/{team['id']}/skills",
        json={"skill_ids": [skill["id"]]},
        headers=OTHER_HEADERS,
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_assign_skills_regardless_of_can_share(client):
    team = await _create_team(client, "Admin Share Team")
    skill = await _create_skill(client, "admin-share-skill")
    r = await client.put(
        f"/api/v1/teams/{team['id']}/skills",
        json={"skill_ids": [skill["id"]]},
        headers=HEADERS,
    )
    assert r.status_code == 200


# --- Add member ---


@pytest.mark.asyncio
async def test_add_member_by_email(client):
    team = await _create_team(client, "Add Member Team")
    await _add_other_user_to_db(client)
    r = await client.post(
        f"/api/v1/teams/{team['id']}/members",
        json={"email": "other@example.com"},
        headers=HEADERS,
    )
    assert r.status_code == 201
    data = r.json()
    assert data["user_id"] == "other-user-id"
    assert data["email"] == "other@example.com"
    assert data["name"] == "Other User"
    assert data["role"] == "member"
    assert data["can_share"] is False


@pytest.mark.asyncio
async def test_add_member_unknown_email_returns_404(client):
    team = await _create_team(client, "Unknown Email Team")
    r = await client.post(
        f"/api/v1/teams/{team['id']}/members",
        json={"email": "nobody@example.com"},
        headers=HEADERS,
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_add_duplicate_member_returns_409(client):
    team = await _create_team(client, "Dup Member Team")
    await _add_other_user_to_db(client)
    await client.post(
        f"/api/v1/teams/{team['id']}/members",
        json={"email": "other@example.com"},
        headers=HEADERS,
    )
    r = await client.post(
        f"/api/v1/teams/{team['id']}/members",
        json={"email": "other@example.com"},
        headers=HEADERS,
    )
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_non_admin_cannot_add_member(client):
    team = await _create_team(client, "No Add Team")
    await _add_other_user_to_db(client)
    r = await client.post(
        f"/api/v1/teams/{team['id']}/members",
        json={"email": "other@example.com"},
        headers=OTHER_HEADERS,
    )
    assert r.status_code == 403


# --- Update member ---


@pytest.mark.asyncio
async def test_toggle_can_share(client):
    team = await _create_team(client, "Toggle Team")
    member = await _add_member_to_team(client, team["id"])
    r = await client.patch(
        f"/api/v1/teams/{team['id']}/members/{member['id']}",
        json={"can_share": True},
        headers=HEADERS,
    )
    assert r.status_code == 200
    assert r.json()["can_share"] is True


@pytest.mark.asyncio
async def test_change_member_role(client):
    team = await _create_team(client, "Role Team")
    member = await _add_member_to_team(client, team["id"])
    r = await client.patch(
        f"/api/v1/teams/{team['id']}/members/{member['id']}",
        json={"role": "admin"},
        headers=HEADERS,
    )
    assert r.status_code == 200
    assert r.json()["role"] == "admin"


@pytest.mark.asyncio
async def test_non_admin_cannot_update_member(client):
    team = await _create_team(client, "No Update Team")
    member = await _add_member_to_team(client, team["id"])
    r = await client.patch(
        f"/api/v1/teams/{team['id']}/members/{member['id']}",
        json={"can_share": True},
        headers=OTHER_HEADERS,
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_cannot_demote_last_admin(client):
    team = await _create_team(client, "Last Admin Team")
    detail = await client.get(f"/api/v1/teams/{team['id']}", headers=HEADERS)
    admin_member = detail.json()["members"][0]
    r = await client.patch(
        f"/api/v1/teams/{team['id']}/members/{admin_member['id']}",
        json={"role": "member"},
        headers=HEADERS,
    )
    assert r.status_code == 400
    assert "last team admin" in r.json()["detail"]


@pytest.mark.asyncio
async def test_can_demote_admin_if_another_exists(client):
    team = await _create_team(client, "Multi Admin Team")
    member = await _add_member_to_team(client, team["id"])
    await client.patch(
        f"/api/v1/teams/{team['id']}/members/{member['id']}",
        json={"role": "admin"},
        headers=HEADERS,
    )
    detail = await client.get(f"/api/v1/teams/{team['id']}", headers=HEADERS)
    original_admin = [m for m in detail.json()["members"] if m["user_id"] == "test-user-id"][0]
    r = await client.patch(
        f"/api/v1/teams/{team['id']}/members/{original_admin['id']}",
        json={"role": "member"},
        headers=HEADERS,
    )
    assert r.status_code == 200
    assert r.json()["role"] == "member"


@pytest.mark.asyncio
async def test_get_team_members_include_email_name(client):
    team = await _create_team(client, "Email Team")
    await _add_other_user_to_db(client)
    detail = await client.get(f"/api/v1/teams/{team['id']}", headers=HEADERS)
    members = detail.json()["members"]
    assert members[0]["email"] == "test@example.com"
    assert members[0]["name"] == "Test User"


# --- Remove member ---


@pytest.mark.asyncio
async def test_remove_member(client):
    team = await _create_team(client, "Remove Member Team")
    member = await _add_member_to_team(client, team["id"])
    r = await client.delete(
        f"/api/v1/teams/{team['id']}/members/{member['id']}",
        headers=HEADERS,
    )
    assert r.status_code == 204
    # Verify member is gone
    detail = await client.get(f"/api/v1/teams/{team['id']}", headers=HEADERS)
    member_ids = [m["id"] for m in detail.json()["members"]]
    assert member["id"] not in member_ids


@pytest.mark.asyncio
async def test_remove_missing_member_returns_404(client):
    team = await _create_team(client, "Remove Missing Team")
    r = await client.delete(
        f"/api/v1/teams/{team['id']}/members/nonexistent",
        headers=HEADERS,
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_cannot_remove_last_admin(client):
    team = await _create_team(client, "Remove Last Admin Team")
    # Add other user as admin
    member = await _add_member_to_team(client, team["id"])
    await client.patch(
        f"/api/v1/teams/{team['id']}/members/{member['id']}",
        json={"role": "admin"},
        headers=HEADERS,
    )
    # Demote the owner to member
    detail = await client.get(f"/api/v1/teams/{team['id']}", headers=HEADERS)
    owner_member = [m for m in detail.json()["members"] if m["user_id"] == "test-user-id"][0]
    await client.patch(
        f"/api/v1/teams/{team['id']}/members/{owner_member['id']}",
        json={"role": "member"},
        headers=HEADERS,
    )
    # Now other-user is the only admin. They try to remove themselves.
    r = await client.delete(
        f"/api/v1/teams/{team['id']}/members/{member['id']}",
        headers=OTHER_HEADERS,
    )
    assert r.status_code == 400
    assert "last team admin" in r.json()["detail"]


@pytest.mark.asyncio
async def test_cannot_remove_team_owner(client):
    team = await _create_team(client, "Remove Owner Team")
    # Add another admin so the "last admin" check won't trigger
    member = await _add_member_to_team(client, team["id"])
    await client.patch(
        f"/api/v1/teams/{team['id']}/members/{member['id']}",
        json={"role": "admin"},
        headers=HEADERS,
    )
    detail = await client.get(f"/api/v1/teams/{team['id']}", headers=HEADERS)
    owner_member = [m for m in detail.json()["members"] if m["user_id"] == "test-user-id"][0]
    r = await client.delete(
        f"/api/v1/teams/{team['id']}/members/{owner_member['id']}",
        headers=HEADERS,
    )
    assert r.status_code == 400
    assert "team owner" in r.json()["detail"]


@pytest.mark.asyncio
async def test_non_admin_cannot_remove_member(client):
    team = await _create_team(client, "No Remove Team")
    member = await _add_member_to_team(client, team["id"])
    r = await client.delete(
        f"/api/v1/teams/{team['id']}/members/{member['id']}",
        headers=OTHER_HEADERS,
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_update_member_requires_at_least_one_field(client):
    team = await _create_team(client, "No Field Team")
    member = await _add_member_to_team(client, team["id"])
    r = await client.patch(
        f"/api/v1/teams/{team['id']}/members/{member['id']}",
        json={},
        headers=HEADERS,
    )
    assert r.status_code == 422


# --- Cross-team skill copy ---


async def _create_skill_full(client, name, scope="team", visibility="open", content="skill content"):
    r = await client.post(
        "/api/v1/skills",
        json={"name": name, "content": content, "scope": scope, "visibility": visibility},
        headers=HEADERS,
    )
    assert r.status_code == 201
    return r.json()


async def _assign_skill_to_team(client, team_id, skill_id):
    r = await client.put(
        f"/api/v1/teams/{team_id}/skills",
        json={"skill_ids": [skill_id]},
        headers=HEADERS,
    )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_copy_own_personal_skill_to_team(client):
    skill = await _create_skill_full(client, "my-personal-skill", scope="personal")
    team = await _create_team(client, "Copy Target Team")
    r = await client.post(
        f"/api/v1/skills/{skill['id']}/copy-to-team/{team['id']}",
        headers=HEADERS,
    )
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "my-personal-skill"
    assert data["target_team_id"] == team["id"]
    assert "id" in data
    assert data["id"] != skill["id"]


@pytest.mark.asyncio
async def test_copy_open_team_skill_to_another_team(client):
    skill = await _create_skill_full(client, "open-team-skill", scope="team", visibility="open")
    source_team = await _create_team(client, "Source Team")
    target_team = await _create_team(client, "Target Team")
    await _assign_skill_to_team(client, source_team["id"], skill["id"])
    r = await client.post(
        f"/api/v1/skills/{skill['id']}/copy-to-team/{target_team['id']}",
        headers=HEADERS,
    )
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "open-team-skill"
    assert data["target_team_id"] == target_team["id"]


@pytest.mark.asyncio
async def test_copy_non_open_team_skill_rejected(client):
    skill = await _create_skill_full(client, "hidden-team-skill", scope="team", visibility="hidden")
    source_team = await _create_team(client, "Hidden Source Team")
    target_team = await _create_team(client, "Hidden Target Team")
    await _assign_skill_to_team(client, source_team["id"], skill["id"])
    r = await client.post(
        f"/api/v1/skills/{skill['id']}/copy-to-team/{target_team['id']}",
        headers=HEADERS,
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_copy_unowned_personal_skill_rejected(client):
    # test_user creates a personal skill; other_user tries to copy it
    skill = await _create_skill_full(client, "others-personal-skill", scope="personal")
    target_team = await _create_team(client, "Other Target Team")
    await _add_other_user_to_db(client)
    await client.post(
        f"/api/v1/teams/{target_team['id']}/members",
        json={"email": "other@example.com"},
        headers=HEADERS,
    )
    # Grant can_share to other_user in target team
    detail = await client.get(f"/api/v1/teams/{target_team['id']}", headers=HEADERS)
    member = [m for m in detail.json()["members"] if m["user_id"] == "other-user-id"][0]
    await client.patch(
        f"/api/v1/teams/{target_team['id']}/members/{member['id']}",
        json={"can_share": True},
        headers=HEADERS,
    )
    r = await client.post(
        f"/api/v1/skills/{skill['id']}/copy-to-team/{target_team['id']}",
        headers=OTHER_HEADERS,
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_copy_to_team_user_not_member_of_rejected(client):
    skill = await _create_skill_full(client, "not-member-skill", scope="personal")
    target_team = await _create_team(client, "Members Only Team")
    r = await client.post(
        f"/api/v1/skills/{skill['id']}/copy-to-team/{target_team['id']}",
        headers=OTHER_HEADERS,
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_copy_without_can_share_in_target_team_rejected(client):
    skill = await _create_skill_full(client, "no-share-perm-skill", scope="team", visibility="open")
    source_team = await _create_team(client, "No Share Source Team")
    target_team = await _create_team(client, "No Share Target Team")
    await _assign_skill_to_team(client, source_team["id"], skill["id"])
    await _add_other_user_to_db(client)
    await client.post(
        f"/api/v1/teams/{source_team['id']}/members",
        json={"email": "other@example.com"},
        headers=HEADERS,
    )
    await client.post(
        f"/api/v1/teams/{target_team['id']}/members",
        json={"email": "other@example.com"},
        headers=HEADERS,
    )
    r = await client.post(
        f"/api/v1/skills/{skill['id']}/copy-to-team/{target_team['id']}",
        headers=OTHER_HEADERS,
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_copy_duplicate_name_in_target_team_rejected(client):
    skill = await _create_skill_full(client, "dup-name-skill", scope="team", visibility="open")
    existing = await _create_skill_full(client, "dup-name-skill-copy", scope="team", visibility="open")
    source_team = await _create_team(client, "Dup Source Team")
    target_team = await _create_team(client, "Dup Target Team")
    await _assign_skill_to_team(client, source_team["id"], skill["id"])
    same_name_skill = await _create_skill_full(client, "dup-name-skill", scope="team", visibility="open")
    await _assign_skill_to_team(client, target_team["id"], same_name_skill["id"])
    r = await client.post(
        f"/api/v1/skills/{skill['id']}/copy-to-team/{target_team['id']}",
        headers=HEADERS,
    )
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_copy_includes_all_skill_files(client):
    skill = await _create_skill_full(client, "multifile-skill", scope="personal")
    await client.post(
        f"/api/v1/skills/{skill['id']}/files",
        json={"path": "ref/a.md", "content": "file a content"},
        headers=HEADERS,
    )
    await client.post(
        f"/api/v1/skills/{skill['id']}/files",
        json={"path": "ref/b.md", "content": "file b content"},
        headers=HEADERS,
    )
    target_team = await _create_team(client, "Multifile Target Team")
    r = await client.post(
        f"/api/v1/skills/{skill['id']}/copy-to-team/{target_team['id']}",
        headers=HEADERS,
    )
    assert r.status_code == 201
    new_skill_id = r.json()["id"]
    files_r = await client.get(f"/api/v1/skills/{new_skill_id}/files", headers=HEADERS)
    assert files_r.status_code == 200
    files = files_r.json()["files"]
    assert len(files) == 2
    paths = {f["path"] for f in files}
    assert paths == {"ref/a.md", "ref/b.md"}


@pytest.mark.asyncio
async def test_copy_is_independent_of_original(client):
    skill = await _create_skill_full(client, "independence-skill", scope="personal", content="original content")
    target_team = await _create_team(client, "Independence Target Team")
    copy_r = await client.post(
        f"/api/v1/skills/{skill['id']}/copy-to-team/{target_team['id']}",
        headers=HEADERS,
    )
    assert copy_r.status_code == 201
    new_id = copy_r.json()["id"]
    await client.put(
        f"/api/v1/skills/{skill['id']}",
        json={"content": "updated content"},
        headers=HEADERS,
    )
    copy_detail = await client.get(f"/api/v1/skills/{new_id}", headers=HEADERS)
    assert copy_detail.status_code == 200
    assert copy_detail.json()["content"] == "original content"


@pytest.mark.asyncio
async def test_same_skill_name_allowed_in_different_teams(client):
    skill1 = await _create_skill_full(client, "shared-name-skill", scope="team", visibility="open")
    skill2 = await _create_skill_full(client, "shared-name-skill", scope="team", visibility="open")
    team1 = await _create_team(client, "Name Team 1")
    team2 = await _create_team(client, "Name Team 2")
    await _assign_skill_to_team(client, team1["id"], skill1["id"])
    await _assign_skill_to_team(client, team2["id"], skill2["id"])
    detail1 = await client.get(f"/api/v1/teams/{team1['id']}", headers=HEADERS)
    detail2 = await client.get(f"/api/v1/teams/{team2['id']}", headers=HEADERS)
    assert "shared-name-skill" in detail1.json()["skills"]
    assert "shared-name-skill" in detail2.json()["skills"]
