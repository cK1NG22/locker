import json


def filter_response(raw_body: bytes, injected_contents: list[str]) -> bytes:
    """Strip injected skill content from LLM response body.

    Scans text blocks in the response content array and removes any
    substring that matches an injected skill's decrypted content.
    Non-text blocks (images, tool_use, etc.) pass through unchanged.

    Args:
        raw_body: Raw response bytes from the LLM API.
        injected_contents: List of decrypted skill content strings that were injected.

    Returns:
        Cleaned response bytes with skill content removed.
    """
    if not injected_contents:
        return raw_body

    try:
        body = json.loads(raw_body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return raw_body

    content_blocks = body.get("content")
    if not isinstance(content_blocks, list):
        return raw_body

    cleaned = False
    for block in content_blocks:
        if not isinstance(block, dict) or block.get("type") != "text":
            continue
        text = block.get("text", "")
        for skill_content in injected_contents:
            if skill_content in text:
                text = text.replace(skill_content, "")
                cleaned = True
        block["text"] = text

    if cleaned:
        return json.dumps(body).encode()
    return raw_body
