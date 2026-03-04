import json
import logging

import httpx

from vault.db import get_db
from vault.crypto import decrypt
from proxy.filter import filter_response

_ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
_MAX_ITERATIONS = 10

logger = logging.getLogger(__name__)


def _extract_ref_requests(response_json: dict) -> list[dict]:
    """Return all tool_use blocks where name == 'locker_read_ref'."""
    content = response_json.get("content", [])
    return [
        block
        for block in content
        if isinstance(block, dict)
        and block.get("type") == "tool_use"
        and block.get("name") == "locker_read_ref"
    ]


async def _resolve_ref(skill_name: str, file_path: str) -> str:
    """Look up a skill by name, then fetch and decrypt the referenced file."""
    db = get_db()

    cursor = await db.execute(
        "SELECT id FROM skills WHERE name = ?", (skill_name,)
    )
    skill_row = await cursor.fetchone()
    if skill_row is None:
        return f"[error] Skill '{skill_name}' not found in vault."

    skill_id = skill_row["id"]

    cursor = await db.execute(
        "SELECT content FROM skill_files WHERE skill_id = ? AND path = ?",
        (skill_id, file_path),
    )
    file_row = await cursor.fetchone()
    if file_row is None:
        return f"[error] File '{file_path}' not found for skill '{skill_name}'."

    return decrypt(file_row["content"])


def _build_tool_results(ref_blocks: list[dict], resolved: dict[str, str]) -> list[dict]:
    """Build tool_result content blocks for each resolved reference.

    Args:
        ref_blocks: The locker_read_ref tool_use blocks from the assistant response.
        resolved: Mapping of tool_use_id -> decrypted content (or error string).

    Returns:
        A list of tool_result content blocks.
    """
    return [
        {
            "type": "tool_result",
            "tool_use_id": block["id"],
            "content": resolved[block["id"]],
        }
        for block in ref_blocks
    ]


def _assistant_message_from_response(response_json: dict) -> dict:
    """Convert the API response into an assistant message for the conversation."""
    return {"role": "assistant", "content": response_json["content"]}


async def handle_ref_requests(
    response_json: dict,
    body: dict,
    forward_headers: dict,
    injected_contents: list[str],
) -> bytes:
    """Handle the tool-use loop for lazy-loading reference files.

    When the LLM responds with locker_read_ref tool calls, this function
    resolves each reference (DB lookup + decryption), feeds the results back
    as tool_result messages, and re-calls the Anthropic API until the LLM
    produces a final response with no more ref requests.

    Args:
        response_json: Parsed JSON from the initial Anthropic API response.
        body: The original request body (with messages).
        forward_headers: Headers to forward to the Anthropic API.
        injected_contents: Decrypted skill content strings for response filtering.

    Returns:
        Final response bytes, filtered to strip injected content.
    """
    ref_blocks = _extract_ref_requests(response_json)

    if not ref_blocks:
        return json.dumps(response_json).encode()

    # Work on a copy of messages so we don't mutate the caller's body
    messages = list(body.get("messages", []))
    current_response = response_json
    current_refs = ref_blocks

    for iteration in range(_MAX_ITERATIONS):
        logger.debug(
            "ref_handler iteration %d: resolving %d reference(s)",
            iteration + 1,
            len(current_refs),
        )

        # Resolve every locker_read_ref in this response
        resolved: dict[str, str] = {}
        for block in current_refs:
            tool_input = block.get("input", {})
            skill_name = tool_input.get("skill_name", "")
            file_path = tool_input.get("file_path", "")
            content = await _resolve_ref(skill_name, file_path)
            resolved[block["id"]] = content
            # Track decrypted file contents for response filtering
            if not content.startswith("[error]"):
                injected_contents.append(content)

        # Append assistant message (the response that contained tool_use)
        messages.append(_assistant_message_from_response(current_response))

        # Append a single user message containing all tool_result blocks
        tool_results = _build_tool_results(current_refs, resolved)
        messages.append({"role": "user", "content": tool_results})

        # Build follow-up request body (preserve model, system, etc.)
        followup_body = {**body, "messages": messages}

        # Send follow-up request to Anthropic
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                _ANTHROPIC_API_URL,
                json=followup_body,
                headers=forward_headers,
                timeout=120.0,
            )

        if resp.status_code != 200:
            # Non-200 means something went wrong; return raw response
            return resp.content

        current_response = resp.json()
        current_refs = _extract_ref_requests(current_response)

        if not current_refs:
            # No more ref requests — we're done
            break
    else:
        logger.warning(
            "ref_handler hit safety limit of %d iterations", _MAX_ITERATIONS
        )

    # Apply response filter to strip injected skill content
    final_bytes = json.dumps(current_response).encode()
    return filter_response(final_bytes, injected_contents)
