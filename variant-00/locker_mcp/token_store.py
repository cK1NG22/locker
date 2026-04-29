"""In-process one-time token store for MCP → proxy skill injection.

Tokens are registered by the MCP server and consumed (destructively) by the proxy.
Each token maps to a skill name and expires after TTL seconds.
"""
import time

# Module-level store shared across all requests in the same process.
_store: dict[str, tuple[str, float]] = {}  # token → (skill_name, expires_at)

TTL = 60  # seconds


def _purge_expired() -> None:
    now = time.time()
    expired = [t for t, (_, exp) in _store.items() if exp <= now]
    for t in expired:
        del _store[t]


def register(token: str, skill_name: str) -> None:
    _purge_expired()
    _store[token] = (skill_name, time.time() + TTL)


def consume(token: str) -> str | None:
    """Return skill_name and remove token, or None if missing/expired."""
    _purge_expired()
    entry = _store.pop(token, None)
    if entry is None:
        return None
    return entry[0]  # skill_name


def _clear() -> None:
    """Test helper — wipes the store."""
    _store.clear()
