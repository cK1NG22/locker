# TODOs

## SSE rate limit counter cleanup
**What:** Add periodic cleanup of the in-memory `_sse_connections` dict in `locker_mcp/sse_server.py`.
**Why:** The dict grows by ~1 entry per unique IP. Without cleanup, it leaks memory over weeks of uptime.
**Where to start:** Add a background task (or inline cleanup every N calls) that prunes IPs with no timestamps newer than `_SSE_RATE_WINDOW`. Alternatively, switch to a TTL-aware data structure.
**Priority:** Low — Railway redeploys reset memory frequently. Only matters if Locker gets sustained traffic from many IPs.

## Port dashboard/ mobile fixes to web/
**What:** Port sidebar/mobile responsive fixes from `dashboard/` to `web/` (Next.js). The hamburger menu and slide-out sidebar built in `dashboard/Sidebar.tsx` need to be replicated in `web/`'s Sidebar component before mobile users hit the app.
**Where to start:** Compare `dashboard/Sidebar.tsx` with `web/`'s equivalent sidebar component. Port the responsive breakpoints, hamburger toggle, and slide-out animation.
**Priority:** Medium — needed before mobile users access the app.
