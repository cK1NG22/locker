import copy
import json
import re
from fastapi import HTTPException
from vault.db import get_db
from vault.crypto import decrypt

_LOCKER_RE = re.compile(r"/locker\s+(\S+)", re.IGNORECASE)
_LOCKER_TOKEN_RE = re.compile(r"\[LOCKER_TOKEN:([0-9a-f-]{36})\]")

_LOCKER_READ_REF_TOOL = {
    "name": "locker_read_ref",
    "description": "Read a reference file from a Locker skill. Returns the file content.",
    "input_schema": {
        "type": "object",
        "properties": {
            "skill_name": {"type": "string", "description": "Name of the skill"},
            "file_path": {"type": "string", "description": "Path of the reference file"},
        },
        "required": ["skill_name", "file_path"],
    },
}


async def _get_skill_files(skill_name: str) -> list[dict]:
    """Query reference files for a skill. Returns list of {path, size_bytes} dicts."""
    db = get_db()
    rows = await db.fetch(
        "SELECT sf.path, sf.size_bytes FROM skill_files sf "
        "JOIN skills s ON s.id = sf.skill_id WHERE s.name = $1",
        skill_name,
    )
    return [{"path": r["path"], "size_bytes": r["size_bytes"]} for r in rows]


def _build_skill_block(skill_name: str, decrypted: str, files: list[dict]) -> str:
    """Build the [SKILL] block, including manifest if reference files exist."""
    block = f"[SKILL: {skill_name}]\n{decrypted}"
    if files:
        lines = ["\n\n[AVAILABLE REFERENCES]"]
        lines.append(
            f'To read a reference, call the `locker_read_ref` tool with '
            f'{{"skill_name": "{skill_name}", "file_path": "..."}}.'
        )
        for f in files:
            lines.append(f"- {f['path']} ({f['size_bytes']:,} bytes)")
        lines.append("[/AVAILABLE REFERENCES]")
        block += "\n".join(lines)
    block += f"\n[/SKILL]"
    return block


def _ensure_ref_tool(body: dict) -> dict:
    """Add the locker_read_ref tool to body['tools'] if not already present."""
    tools = body.get("tools", [])
    for t in tools:
        if t.get("name") == "locker_read_ref":
            return body  # already there
    body["tools"] = tools + [_LOCKER_READ_REF_TOOL]
    return body


def _get_text(content) -> str:
    """Extract plain text from a content field (string or content-block array)."""
    if isinstance(content, str):
        return content
    parts = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
    return "\n".join(parts)


def _set_text(content, new_text: str):
    """Return content with the text replaced by new_text."""
    if isinstance(content, str):
        return new_text
    result = []
    replaced = False
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            if not replaced:
                result.append({**block, "text": new_text})
                replaced = True
            # drop additional text blocks (they were merged above)
        else:
            result.append(block)
    if not replaced:
        result.insert(0, {"type": "text", "text": new_text})
    return result


async def _inject_tokens(body: dict) -> tuple[dict, list[str], bool]:
    """Detect [LOCKER_TOKEN:UUID] in the body, consume from store, inject skills.
    Returns (modified_body, list_of_injected_content_strings, has_ref_files)."""
    from locker_mcp.token_store import consume

    body_str = json.dumps(body)
    token_ids = _LOCKER_TOKEN_RE.findall(body_str)
    if not token_ids:
        return body, [], False

    # Deduplicate while preserving order
    unique_token_ids: list[str] = list(dict.fromkeys(token_ids))

    db = get_db()
    skill_blocks: list[str] = []
    injected_contents: list[str] = []
    has_ref_files = False
    for token_id in unique_token_ids:
        skill_name = consume(token_id)
        if skill_name is None:
            raise HTTPException(
                status_code=422, detail=f"Token '{token_id}' is unknown or expired"
            )
        row = await db.fetchrow(
            "SELECT content FROM skills WHERE name = $1", skill_name
        )
        if row is None:
            raise HTTPException(
                status_code=422, detail=f"Skill '{skill_name}' not found"
            )
        decrypted = decrypt(row["content"])
        files = await _get_skill_files(skill_name)
        if files:
            has_ref_files = True
        skill_blocks.append(_build_skill_block(skill_name, decrypted, files))
        injected_contents.append(decrypted)

    injection = "\n\n".join(skill_blocks)

    # Strip all tokens from body before forwarding
    clean_body_str = _LOCKER_TOKEN_RE.sub("", body_str)
    body = json.loads(clean_body_str)

    existing_system = body.get("system", "")
    body["system"] = (injection + "\n\n" + existing_system) if existing_system else injection

    if has_ref_files:
        body = _ensure_ref_tool(body)

    return body, injected_contents, has_ref_files


async def inject_skills(body: dict) -> tuple[dict, list[str], bool]:
    """
    Scan messages for /locker <name> commands and [LOCKER_TOKEN:UUID] tokens.
    Fetch each skill from the vault, strip triggers, and prepend skill blocks to
    the system prompt. Raises HTTPException(422) if any skill is not found.

    Returns (modified_body, list_of_injected_content_strings, has_ref_files)
    for response filtering and tool-use loop handling.
    """
    messages = body.get("messages", [])
    injected_contents: list[str] = []
    has_ref_files = False

    # Collect unique skill names across all messages (preserve order)
    skill_names: list[str] = []
    for msg in messages:
        text = _get_text(msg.get("content", ""))
        for name in _LOCKER_RE.findall(text):
            if name not in skill_names:
                skill_names.append(name)

    if skill_names:
        # Fetch and decrypt each skill
        db = get_db()
        skill_blocks: list[str] = []
        for name in skill_names:
            row = await db.fetchrow(
                "SELECT content FROM skills WHERE name = $1", name
            )
            if row is None:
                raise HTTPException(status_code=422, detail=f"Skill '{name}' not found")
            decrypted = decrypt(row["content"])
            files = await _get_skill_files(name)
            if files:
                has_ref_files = True
            skill_blocks.append(_build_skill_block(name, decrypted, files))
            injected_contents.append(decrypted)

        injection = "\n\n".join(skill_blocks)

        body = copy.deepcopy(body)

        # Prepend injection to system prompt
        existing_system = body.get("system", "")
        body["system"] = (injection + "\n\n" + existing_system) if existing_system else injection

        if has_ref_files:
            body = _ensure_ref_tool(body)

        # Strip /locker commands from message text
        new_messages = []
        for msg in messages:
            content = msg.get("content", "")
            text = _get_text(content)
            clean_text = _LOCKER_RE.sub("", text).strip()
            new_msg = dict(msg)
            new_msg["content"] = _set_text(content, clean_text)
            new_messages.append(new_msg)
        body["messages"] = new_messages

    # Phase 2: MCP token injection (runs regardless of /locker commands)
    body, token_contents, token_has_refs = await _inject_tokens(body)
    injected_contents.extend(token_contents)
    if token_has_refs:
        has_ref_files = True

    return body, injected_contents, has_ref_files
