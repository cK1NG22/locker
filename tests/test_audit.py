"""Tests for audit logging (vault/audit.py)."""

import json
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from tests.conftest import TEST_JWT, OTHER_JWT
from main import app
from vault.db import init_db, close_db, get_db
from vault.audit import audit

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


# --- 1. audit() helper inserts a row ---

@pytest.mark.asyncio
async def test_audit_helper_inserts_row(client):
    db = get_db()
    await audit(db, "user-1", "skill.create", "skill", "sk-123", {"name": "my-skill"})

    row = await db.fetchrow("SELECT * FROM audit_logs WHERE actor_id = $1", "user-1")
    assert row is not None
    assert row["action"] == "skill.create"
    assert row["resource_type"] == "skill"
    assert row["resource_id"] == "sk-123"
    meta = json.loads(row["metadata"])
    assert meta["name"] == "my-skill"
    assert row["created_at"] is not None


# --- 2. audit() fire-and-forget — never raises ---

@pytest.mark.asyncio
async def test_audit_helper_fire_and_forget():
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=RuntimeError("DB is down"))

    # Should complete without raising
    await audit(mock_db, "user-1", "skill.create", "skill", "sk-123")


# --- 3. GET /audit-log returns empty list ---

@pytest.mark.asyncio
async def test_get_audit_log_empty(client):
    r = await client.get("/api/v1/audit-log", headers=HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert body["logs"] == []
    assert body["total"] == 0


# --- 4. GET /audit-log returns inserted logs ---

@pytest.mark.asyncio
async def test_get_audit_log_returns_logs(client):
    db = get_db()
    await audit(db, "user-1", "skill.create", "skill", "sk-1", {"name": "alpha"})
    await audit(db, "user-2", "skill.delete", "skill", "sk-2")
    await audit(db, "user-1", "team.create", "team", "tm-1", {"name": "ops"})

    r = await client.get("/api/v1/audit-log", headers=HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 3
    assert len(body["logs"]) == 3
    # Most recent first
    actions = [log["action"] for log in body["logs"]]
    assert "skill.create" in actions
    assert "skill.delete" in actions
    assert "team.create" in actions


# --- 5. GET /audit-log with filters ---

@pytest.mark.asyncio
async def test_get_audit_log_filters(client):
    db = get_db()
    await audit(db, "user-1", "skill.create", "skill", "sk-1")
    await audit(db, "user-2", "skill.delete", "skill", "sk-2")
    await audit(db, "user-1", "team.create", "team", "tm-1")

    # Filter by action
    r = await client.get("/api/v1/audit-log?action=skill.create", headers=HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["logs"][0]["action"] == "skill.create"

    # Filter by resource_type
    r = await client.get("/api/v1/audit-log?resource_type=team", headers=HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["logs"][0]["resource_type"] == "team"

    # Filter by actor_id
    r = await client.get("/api/v1/audit-log?actor_id=user-1", headers=HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2
    assert all(log["actor_id"] == "user-1" for log in body["logs"])

    # Filter by date range
    r = await client.get(
        "/api/v1/audit-log?from_date=2020-01-01T00:00:00&to_date=2099-12-31T23:59:59",
        headers=HEADERS,
    )
    assert r.status_code == 200
    assert r.json()["total"] == 3


# --- 6. GET /audit-log requires auth ---

@pytest.mark.asyncio
async def test_get_audit_log_requires_auth(client):
    r = await client.get("/api/v1/audit-log")
    assert r.status_code == 401


# --- 7. Skill create produces audit log ---

@pytest.mark.asyncio
async def test_skill_create_produces_audit_log(client):
    r = await client.post(
        "/api/v1/skills",
        json={"name": "audited-skill", "content": "Do the thing."},
        headers=HEADERS,
    )
    assert r.status_code == 201
    skill_id = r.json()["id"]

    r = await client.get("/api/v1/audit-log?action=skill.create", headers=HEADERS)
    assert r.status_code == 200
    logs = r.json()["logs"]
    matching = [entry for entry in logs if entry["resource_id"] == skill_id]
    assert len(matching) == 1
    assert matching[0]["resource_type"] == "skill"
    assert matching[0]["actor_id"] == "test-user-id"


# --- 8. Skill delete produces audit log ---

@pytest.mark.asyncio
async def test_skill_delete_produces_audit_log(client):
    # Create a skill first
    r = await client.post(
        "/api/v1/skills",
        json={"name": "to-delete", "content": "Bye."},
        headers=HEADERS,
    )
    assert r.status_code == 201
    skill_id = r.json()["id"]

    # Delete it
    r = await client.delete(f"/api/v1/skills/{skill_id}", headers=HEADERS)
    assert r.status_code == 204

    # Check audit log
    r = await client.get("/api/v1/audit-log?action=skill.delete", headers=HEADERS)
    assert r.status_code == 200
    logs = r.json()["logs"]
    matching = [entry for entry in logs if entry["resource_id"] == skill_id]
    assert len(matching) == 1
    assert matching[0]["resource_type"] == "skill"
    assert matching[0]["actor_id"] == "test-user-id"


# --- 9. Team create produces audit log ---

@pytest.mark.asyncio
async def test_team_create_produces_audit_log(client):
    r = await client.post(
        "/api/v1/teams",
        json={"name": "audited-team"},
        headers=HEADERS,
    )
    assert r.status_code == 201
    team_id = r.json()["id"]

    r = await client.get("/api/v1/audit-log?action=team.create", headers=HEADERS)
    assert r.status_code == 200
    logs = r.json()["logs"]
    matching = [entry for entry in logs if entry["resource_id"] == team_id]
    assert len(matching) == 1
    assert matching[0]["resource_type"] == "team"
    assert matching[0]["actor_id"] == "test-user-id"
