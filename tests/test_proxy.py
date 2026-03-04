import base64
import json
import os
import pytest
import pytest_asyncio
import respx
import httpx
from httpx import AsyncClient, ASGITransport
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Set env vars before app import
TEST_API_KEY = "test-api-key-proxy"
TEST_ENC_KEY = base64.b64encode(AESGCM.generate_key(256)).decode()

os.environ["LOCKER_API_KEY"] = TEST_API_KEY
os.environ["LOCKER_ENCRYPTION_KEY"] = TEST_ENC_KEY
os.environ["LOCKER_DB_PATH"] = ":memory:"
os.environ["ANTHROPIC_API_KEY"] = "test-anthropic-key"

from main import app  # noqa: E402
from vault.db import init_db, close_db  # noqa: E402

FAKE_ANTHROPIC_RESPONSE = {
    "id": "msg_test",
    "type": "message",
    "role": "assistant",
    "content": [{"type": "text", "text": "Hello from mock Anthropic"}],
    "model": "claude-opus-4-6",
    "stop_reason": "end_turn",
    "usage": {"input_tokens": 10, "output_tokens": 5},
}


@pytest_asyncio.fixture
async def client():
    await init_db()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
    await close_db()


async def _create_skill(client, name: str, content: str) -> str:
    headers = {"X-API-Key": os.environ["LOCKER_API_KEY"]}
    r = await client.post(
        "/api/v1/skills",
        json={"name": name, "content": content},
        headers=headers,
    )
    assert r.status_code == 201
    return r.json()["id"]


def _mock_anthropic():
    """Return a respx route mock for the Anthropic messages endpoint."""
    return respx.post("https://api.anthropic.com/v1/messages").mock(
        return_value=httpx.Response(200, json=FAKE_ANTHROPIC_RESPONSE)
    )


# --- Tests ---


@pytest.mark.asyncio
async def test_no_locker_command_passes_through(client):
    """No /locker command — request passes through; system prompt untouched."""
    payload = {
        "model": "claude-opus-4-6",
        "system": "You are helpful.",
        "messages": [{"role": "user", "content": "Hello"}],
        "max_tokens": 100,
    }
    with respx.mock:
        route = _mock_anthropic()
        r = await client.post("/proxy/anthropic/v1/messages", json=payload)
        assert r.status_code == 200
        forwarded_body = json.loads(route.calls[0].request.content)

    assert forwarded_body["system"] == "You are helpful."
    assert forwarded_body["messages"][0]["content"] == "Hello"


@pytest.mark.asyncio
async def test_single_locker_string_content(client):
    """Single /locker with plain string content — skill injected, command stripped."""
    await _create_skill(client, "email-style", "Always write concise emails.")

    payload = {
        "model": "claude-opus-4-6",
        "messages": [{"role": "user", "content": "/locker email-style Write me an email."}],
        "max_tokens": 100,
    }
    with respx.mock:
        route = _mock_anthropic()
        r = await client.post("/proxy/anthropic/v1/messages", json=payload)
        assert r.status_code == 200
        forwarded_body = json.loads(route.calls[0].request.content)

    assert "[SKILL: email-style]" in forwarded_body["system"]
    assert "Always write concise emails." in forwarded_body["system"]
    assert "[/SKILL]" in forwarded_body["system"]
    assert "/locker" not in forwarded_body["messages"][0]["content"]
    assert "Write me an email." in forwarded_body["messages"][0]["content"]


@pytest.mark.asyncio
async def test_single_locker_content_block_array(client):
    """Single /locker with content-block array format — skill injected, command stripped."""
    await _create_skill(client, "tone-formal", "Use formal language at all times.")

    payload = {
        "model": "claude-opus-4-6",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "/locker tone-formal Please reply."}
                ],
            }
        ],
        "max_tokens": 100,
    }
    with respx.mock:
        route = _mock_anthropic()
        r = await client.post("/proxy/anthropic/v1/messages", json=payload)
        assert r.status_code == 200
        forwarded_body = json.loads(route.calls[0].request.content)

    assert "[SKILL: tone-formal]" in forwarded_body["system"]
    msg_content = forwarded_body["messages"][0]["content"]
    assert isinstance(msg_content, list)
    text_block = next(b for b in msg_content if b.get("type") == "text")
    assert "/locker" not in text_block["text"]
    assert "Please reply." in text_block["text"]


@pytest.mark.asyncio
async def test_unknown_skill_returns_422(client):
    """Unknown skill name — returns 422 with a clear message."""
    payload = {
        "model": "claude-opus-4-6",
        "messages": [{"role": "user", "content": "/locker does-not-exist Hello"}],
        "max_tokens": 100,
    }
    r = await client.post("/proxy/anthropic/v1/messages", json=payload)
    assert r.status_code == 422
    assert "does-not-exist" in r.json()["detail"]


@pytest.mark.asyncio
async def test_multiple_locker_commands(client):
    """Multiple /locker commands — all skills injected as separate blocks."""
    await _create_skill(client, "skill-alpha", "Alpha skill content.")
    await _create_skill(client, "skill-beta", "Beta skill content.")

    payload = {
        "model": "claude-opus-4-6",
        "messages": [
            {"role": "user", "content": "/locker skill-alpha /locker skill-beta Do the thing."}
        ],
        "max_tokens": 100,
    }
    with respx.mock:
        route = _mock_anthropic()
        r = await client.post("/proxy/anthropic/v1/messages", json=payload)
        assert r.status_code == 200
        forwarded_body = json.loads(route.calls[0].request.content)

    system = forwarded_body["system"]
    assert "[SKILL: skill-alpha]" in system
    assert "Alpha skill content." in system
    assert "[SKILL: skill-beta]" in system
    assert "Beta skill content." in system
    assert "/locker" not in forwarded_body["messages"][0]["content"]


@pytest.mark.asyncio
async def test_existing_system_prompt_preserved(client):
    """Skill is prepended; original system prompt is kept intact."""
    await _create_skill(client, "prepend-skill", "Prepended content.")

    payload = {
        "model": "claude-opus-4-6",
        "system": "Original system instructions.",
        "messages": [{"role": "user", "content": "/locker prepend-skill Go."}],
        "max_tokens": 100,
    }
    with respx.mock:
        route = _mock_anthropic()
        r = await client.post("/proxy/anthropic/v1/messages", json=payload)
        assert r.status_code == 200
        forwarded_body = json.loads(route.calls[0].request.content)

    system = forwarded_body["system"]
    assert "[SKILL: prepend-skill]" in system
    assert "Prepended content." in system
    assert "Original system instructions." in system
    assert system.index("[SKILL: prepend-skill]") < system.index("Original system instructions.")


@pytest.mark.asyncio
async def test_no_system_prompt_created_from_skill(client):
    """No existing system prompt — system prompt is created from skill content."""
    await _create_skill(client, "solo-skill", "Solo skill content.")

    payload = {
        "model": "claude-opus-4-6",
        "messages": [{"role": "user", "content": "/locker solo-skill Hello."}],
        "max_tokens": 100,
    }
    with respx.mock:
        route = _mock_anthropic()
        r = await client.post("/proxy/anthropic/v1/messages", json=payload)
        assert r.status_code == 200
        forwarded_body = json.loads(route.calls[0].request.content)

    assert "system" in forwarded_body
    assert "[SKILL: solo-skill]" in forwarded_body["system"]
    assert "Solo skill content." in forwarded_body["system"]


# --- Response filtering integration tests ---


def _mock_anthropic_echo(skill_content: str):
    """Mock Anthropic to echo back skill content in its response."""
    echo_response = {
        "id": "msg_test",
        "type": "message",
        "role": "assistant",
        "content": [{"type": "text", "text": f"Sure! {skill_content} Here you go."}],
        "model": "claude-opus-4-6",
        "stop_reason": "end_turn",
        "usage": {"input_tokens": 10, "output_tokens": 5},
    }
    return respx.post("https://api.anthropic.com/v1/messages").mock(
        return_value=httpx.Response(200, json=echo_response)
    )


@pytest.mark.asyncio
async def test_response_filters_echoed_skill_content(client):
    """If Anthropic echoes injected skill content, it is stripped from the response."""
    skill_content = "Top secret email formula XYZ."
    await _create_skill(client, "secret-skill", skill_content)

    payload = {
        "model": "claude-opus-4-6",
        "messages": [{"role": "user", "content": "/locker secret-skill Write an email."}],
        "max_tokens": 100,
    }
    with respx.mock:
        _mock_anthropic_echo(skill_content)
        r = await client.post("/proxy/anthropic/v1/messages", json=payload)
        assert r.status_code == 200

    body = r.json()
    response_text = body["content"][0]["text"]
    assert skill_content not in response_text
    assert "Sure!" in response_text
    assert "Here you go." in response_text


@pytest.mark.asyncio
async def test_response_no_filtering_without_injection(client):
    """No skills injected — response passes through unmodified."""
    payload = {
        "model": "claude-opus-4-6",
        "messages": [{"role": "user", "content": "Hello"}],
        "max_tokens": 100,
    }
    with respx.mock:
        _mock_anthropic()
        r = await client.post("/proxy/anthropic/v1/messages", json=payload)
        assert r.status_code == 200

    body = r.json()
    assert body["content"][0]["text"] == "Hello from mock Anthropic"


# --- Helper: create skill with reference files ---


async def _create_skill_with_files(client, name: str, content: str, files: list[dict]) -> str:
    headers = {"X-API-Key": os.environ["LOCKER_API_KEY"]}
    r = await client.post(
        "/api/v1/skills",
        json={"name": name, "content": content},
        headers=headers,
    )
    assert r.status_code == 201
    skill_id = r.json()["id"]
    for f in files:
        r2 = await client.post(
            f"/api/v1/skills/{skill_id}/files",
            json={"path": f["path"], "content": f["content"]},
            headers=headers,
        )
        assert r2.status_code == 201
    return skill_id


# --- Manifest injection + ref handler tests ---


@pytest.mark.asyncio
async def test_skill_with_files_injects_manifest(client):
    """Skill with reference files — manifest and locker_read_ref tool are injected."""
    await _create_skill_with_files(
        client,
        "research-skill",
        "Use the references to answer questions.",
        [{"path": "data/report.md", "content": "Quarterly earnings report content."}],
    )

    payload = {
        "model": "claude-opus-4-6",
        "messages": [{"role": "user", "content": "/locker research-skill Summarize the report."}],
        "max_tokens": 100,
    }
    with respx.mock:
        route = _mock_anthropic()
        r = await client.post("/proxy/anthropic/v1/messages", json=payload)
        assert r.status_code == 200
        forwarded_body = json.loads(route.calls[0].request.content)

    # Manifest appears in the system prompt
    system = forwarded_body["system"]
    assert "[AVAILABLE REFERENCES]" in system
    assert "data/report.md" in system
    assert "bytes" in system  # size_bytes annotation

    # locker_read_ref tool is registered in the tools array
    tools = forwarded_body.get("tools", [])
    tool_names = [t["name"] for t in tools]
    assert "locker_read_ref" in tool_names


@pytest.mark.asyncio
async def test_skill_without_files_no_manifest(client):
    """Skill with NO reference files — no manifest, no locker_read_ref tool."""
    await _create_skill(client, "plain-skill", "Just a plain skill with no files.")

    payload = {
        "model": "claude-opus-4-6",
        "messages": [{"role": "user", "content": "/locker plain-skill Do something."}],
        "max_tokens": 100,
    }
    with respx.mock:
        route = _mock_anthropic()
        r = await client.post("/proxy/anthropic/v1/messages", json=payload)
        assert r.status_code == 200
        forwarded_body = json.loads(route.calls[0].request.content)

    # No manifest in system prompt
    system = forwarded_body["system"]
    assert "[AVAILABLE REFERENCES]" not in system

    # No locker_read_ref tool registered
    tools = forwarded_body.get("tools", [])
    tool_names = [t.get("name") for t in tools]
    assert "locker_read_ref" not in tool_names


@pytest.mark.asyncio
async def test_ref_handler_resolves_tool_use(client):
    """Ref handler loop: LLM requests a file via tool_use, gets content, returns final text."""
    file_content = "Secret reference file data for analysis."
    await _create_skill_with_files(
        client,
        "ref-loop-skill",
        "Analyze the reference files.",
        [{"path": "refs/analysis.txt", "content": file_content}],
    )

    payload = {
        "model": "claude-opus-4-6",
        "messages": [{"role": "user", "content": "/locker ref-loop-skill Analyze the data."}],
        "max_tokens": 200,
    }

    # First Anthropic response: tool_use requesting the reference file
    tool_use_response = httpx.Response(
        200,
        json={
            "id": "msg_test",
            "type": "message",
            "role": "assistant",
            "content": [
                {
                    "type": "tool_use",
                    "id": "toolu_123",
                    "name": "locker_read_ref",
                    "input": {
                        "skill_name": "ref-loop-skill",
                        "file_path": "refs/analysis.txt",
                    },
                }
            ],
            "model": "claude-opus-4-6",
            "stop_reason": "tool_use",
            "usage": {"input_tokens": 10, "output_tokens": 5},
        },
    )

    # Second Anthropic response: final text answer (includes file content to test filtering)
    final_response = httpx.Response(
        200,
        json={
            "id": "msg_test2",
            "type": "message",
            "role": "assistant",
            "content": [
                {
                    "type": "text",
                    "text": f"Based on my analysis: {file_content} The data looks good.",
                }
            ],
            "model": "claude-opus-4-6",
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 50, "output_tokens": 20},
        },
    )

    with respx.mock:
        respx.post("https://api.anthropic.com/v1/messages").mock(
            side_effect=[tool_use_response, final_response]
        )
        r = await client.post("/proxy/anthropic/v1/messages", json=payload)
        assert r.status_code == 200

    body = r.json()
    response_text = body["content"][0]["text"]

    # Final response text is returned to client
    assert "Based on my analysis:" in response_text
    assert "The data looks good." in response_text

    # Injected skill content is filtered out of the final response
    assert "Analyze the reference files." not in response_text
    # Reference file content is also filtered (it was injected via tool_result)
    assert file_content not in response_text
