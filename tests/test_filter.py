import json
import pytest

from proxy.filter import filter_response


def _make_response(content_blocks: list) -> bytes:
    """Build a fake Anthropic response body."""
    return json.dumps({
        "id": "msg_test",
        "type": "message",
        "role": "assistant",
        "content": content_blocks,
        "model": "claude-opus-4-6",
        "stop_reason": "end_turn",
        "usage": {"input_tokens": 10, "output_tokens": 5},
    }).encode()


class TestFilterResponse:
    def test_echoed_content_stripped(self):
        """If the LLM echoes injected skill content, it gets removed."""
        skill_content = "Always write concise emails."
        raw = _make_response([
            {"type": "text", "text": f"Sure! {skill_content} Here's your email."}
        ])
        result = json.loads(filter_response(raw, [skill_content]))
        assert skill_content not in result["content"][0]["text"]
        assert "Sure!" in result["content"][0]["text"]
        assert "Here's your email." in result["content"][0]["text"]

    def test_non_echo_passes_through(self):
        """Response without injected content passes through unchanged."""
        raw = _make_response([
            {"type": "text", "text": "Hello, how can I help you?"}
        ])
        result = filter_response(raw, ["Some skill content not in response"])
        assert result == raw

    def test_non_text_blocks_untouched(self):
        """Non-text blocks (tool_use, images) pass through unchanged."""
        tool_block = {"type": "tool_use", "id": "tool_1", "name": "calc", "input": {"x": 1}}
        skill_content = "secret formula"
        raw = _make_response([
            tool_block,
            {"type": "text", "text": f"Result: {skill_content} done."}
        ])
        result = json.loads(filter_response(raw, [skill_content]))
        assert result["content"][0] == tool_block
        assert skill_content not in result["content"][1]["text"]

    def test_no_injection_no_filtering(self):
        """Empty injected_contents list means no filtering."""
        raw = _make_response([
            {"type": "text", "text": "Normal response here."}
        ])
        result = filter_response(raw, [])
        assert result == raw

    def test_multiple_skill_contents_stripped(self):
        """Multiple injected skills are all stripped from the response."""
        skill_a = "Alpha skill content."
        skill_b = "Beta skill content."
        raw = _make_response([
            {"type": "text", "text": f"Here is {skill_a} and also {skill_b} in the response."}
        ])
        result = json.loads(filter_response(raw, [skill_a, skill_b]))
        text = result["content"][0]["text"]
        assert skill_a not in text
        assert skill_b not in text
        assert "Here is" in text

    def test_multiple_text_blocks_all_filtered(self):
        """Skill content is stripped from every text block in the response."""
        skill_content = "secret instructions"
        raw = _make_response([
            {"type": "text", "text": f"Block 1: {skill_content}"},
            {"type": "text", "text": f"Block 2: {skill_content}"},
        ])
        result = json.loads(filter_response(raw, [skill_content]))
        for block in result["content"]:
            assert skill_content not in block["text"]

    def test_invalid_json_passes_through(self):
        """Non-JSON response body passes through unchanged."""
        raw = b"not valid json"
        result = filter_response(raw, ["some content"])
        assert result == raw

    def test_no_content_key_passes_through(self):
        """Response without content array passes through unchanged."""
        raw = json.dumps({"error": "something"}).encode()
        result = filter_response(raw, ["some content"])
        assert result == raw
