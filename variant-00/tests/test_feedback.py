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


async def _create_skill_and_team(client):
    """Create a skill and team, return (skill_id, team_token)."""
    skill = await client.post(
        "/api/v1/skills",
        json={"name": "test-skill", "content": "skill content", "visibility": "open"},
        headers=ADMIN,
    )
    skill_id = skill.json()["id"]

    team = await client.post(
        "/api/v1/teams", json={"name": "FeedbackTeam"}, headers=ADMIN
    )
    team_data = team.json()
    await client.put(
        f"/api/v1/teams/{team_data['id']}/skills",
        json={"skill_ids": [skill_id]},
        headers=ADMIN,
    )
    return skill_id, team_data["token"]


@pytest.mark.asyncio
async def test_submit_feedback(client):
    skill_id, token = await _create_skill_and_team(client)
    r = await client.post(
        f"/api/v1/skills/{skill_id}/feedback",
        json={"feedback_text": "This skill needs more examples"},
        headers={"X-Team-Token": token},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["skill_id"] == skill_id
    assert data["feedback_text"] == "This skill needs more examples"
    assert data["status"] == "pending"
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_get_feedback_admin(client):
    skill_id, token = await _create_skill_and_team(client)
    await client.post(
        f"/api/v1/skills/{skill_id}/feedback",
        json={"feedback_text": "Needs improvement"},
        headers={"X-Team-Token": token},
    )
    r = await client.get("/api/v1/feedback", headers=ADMIN)
    assert r.status_code == 200
    feedback_list = r.json()["feedback"]
    assert len(feedback_list) >= 1
    assert feedback_list[0]["feedback_text"] == "Needs improvement"


@pytest.mark.asyncio
async def test_update_feedback_status(client):
    skill_id, token = await _create_skill_and_team(client)
    submit = await client.post(
        f"/api/v1/skills/{skill_id}/feedback",
        json={"feedback_text": "Review this please"},
        headers={"X-Team-Token": token},
    )
    feedback_id = submit.json()["id"]
    r = await client.patch(
        f"/api/v1/feedback/{feedback_id}",
        json={"status": "reviewed"},
        headers=ADMIN,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "reviewed"


@pytest.mark.asyncio
async def test_feedback_filter_by_status(client):
    skill_id, token = await _create_skill_and_team(client)
    f1 = await client.post(
        f"/api/v1/skills/{skill_id}/feedback",
        json={"feedback_text": "First feedback"},
        headers={"X-Team-Token": token},
    )
    await client.post(
        f"/api/v1/skills/{skill_id}/feedback",
        json={"feedback_text": "Second feedback"},
        headers={"X-Team-Token": token},
    )
    await client.patch(
        f"/api/v1/feedback/{f1.json()['id']}",
        json={"status": "reviewed"},
        headers=ADMIN,
    )
    r = await client.get("/api/v1/feedback?status=pending", headers=ADMIN)
    assert r.status_code == 200
    pending = r.json()["feedback"]
    assert len(pending) == 1
    assert pending[0]["feedback_text"] == "Second feedback"
    r2 = await client.get("/api/v1/feedback?status=reviewed", headers=ADMIN)
    reviewed = r2.json()["feedback"]
    assert len(reviewed) == 1
    assert reviewed[0]["feedback_text"] == "First feedback"


@pytest.mark.asyncio
async def test_feedback_requires_team_token(client):
    skill_id, _token = await _create_skill_and_team(client)
    r = await client.post(
        f"/api/v1/skills/{skill_id}/feedback",
        json={"feedback_text": "No token"},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_feedback_admin_requires_auth(client):
    r = await client.get("/api/v1/feedback")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_feedback_includes_skill_name(client):
    skill_id, token = await _create_skill_and_team(client)
    await client.post(
        f"/api/v1/skills/{skill_id}/feedback",
        json={"feedback_text": "Skill name test"},
        headers={"X-Team-Token": token},
    )
    r = await client.get("/api/v1/feedback", headers=ADMIN)
    assert r.status_code == 200
    item = r.json()["feedback"][0]
    assert item["skill_name"] == "test-skill"


@pytest.mark.asyncio
async def test_feedback_excludes_submitter_by_default(client):
    skill_id, token = await _create_skill_and_team(client)
    await client.post(
        f"/api/v1/skills/{skill_id}/feedback",
        json={"feedback_text": "Privacy test"},
        headers={"X-Team-Token": token},
    )
    r = await client.get("/api/v1/feedback", headers=ADMIN)
    assert r.status_code == 200
    item = r.json()["feedback"][0]
    assert "team_id" not in item
    assert "submitter_team_name" not in item


@pytest.mark.asyncio
async def test_feedback_includes_submitter_when_requested(client):
    skill_id, token = await _create_skill_and_team(client)
    await client.post(
        f"/api/v1/skills/{skill_id}/feedback",
        json={"feedback_text": "Submitter test"},
        headers={"X-Team-Token": token},
    )
    r = await client.get(
        "/api/v1/feedback?include_submitter=true", headers=ADMIN
    )
    assert r.status_code == 200
    item = r.json()["feedback"][0]
    assert "team_id" in item
    assert item["submitter_team_name"] == "FeedbackTeam"


@pytest.mark.asyncio
async def test_update_feedback_includes_skill_name(client):
    skill_id, token = await _create_skill_and_team(client)
    submit = await client.post(
        f"/api/v1/skills/{skill_id}/feedback",
        json={"feedback_text": "Patch test"},
        headers={"X-Team-Token": token},
    )
    feedback_id = submit.json()["id"]
    r = await client.patch(
        f"/api/v1/feedback/{feedback_id}",
        json={"status": "applied"},
        headers=ADMIN,
    )
    assert r.status_code == 200
    assert r.json()["skill_name"] == "test-skill"
