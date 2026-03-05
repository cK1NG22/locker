import base64
import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from datetime import datetime, timezone

import jwt as _jwt

TEST_JWT_SECRET = "test-jwt-secret-that-is-long-enough-for-hs256"
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
    # Submit two feedback items
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
    # Mark first as reviewed
    await client.patch(
        f"/api/v1/feedback/{f1.json()['id']}",
        json={"status": "reviewed"},
        headers=ADMIN,
    )
    # Filter by pending — should only get second
    r = await client.get("/api/v1/feedback?status=pending", headers=ADMIN)
    assert r.status_code == 200
    pending = r.json()["feedback"]
    assert len(pending) == 1
    assert pending[0]["feedback_text"] == "Second feedback"
    # Filter by reviewed — should only get first
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
