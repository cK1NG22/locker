# TODOs

## SSE rate limit counter cleanup
**What:** Add periodic cleanup of the in-memory `_sse_connections` dict in `locker_mcp/sse_server.py`.
**Why:** The dict grows by ~1 entry per unique IP. Without cleanup, it leaks memory over weeks of uptime.
**Where to start:** Add a background task (or inline cleanup every N calls) that prunes IPs with no timestamps newer than `_SSE_RATE_WINDOW`. Alternatively, switch to a TTL-aware data structure.
**Priority:** Low — Railway redeploys reset memory frequently. Only matters if Locker gets sustained traffic from many IPs.
