# Worktree Task: 4.5 — Rate limiting

## Task ID
4.5

## Branch
`dung/4.5-rate-limiting`

## Description
Add per-IP and per-token rate limiting via `slowapi` middleware. Key limits: employee endpoints (60 req/min per token), admin endpoints (120 req/min per user), auth endpoint (10 req/min per IP). Log rate-limit hits.

## Files to Create/Modify
- `main.py`
- `pyproject.toml`
- New `src/middleware/rate_limit.py`

## Dependencies (all complete)
- None

## Downstream Tasks (blocked by this task)
- None directly

## Key Context
- FastAPI app defined in `main.py`
- Admin routes use `Authorization: Bearer <jwt>` (JWT contains user sub)
- Employee routes use `X-Team-Token` header
- Auth endpoint: `POST /auth/google` in `src/auth/oauth.py`
- Proxy endpoint: `/proxy/anthropic/v1/messages`
- `slowapi` is a popular FastAPI rate-limiting library built on `limits`

## Project References
- Project CLAUDE.md: `../../CLAUDE.md` (from project root)
- Roadmap: `docs/ROADMAP.md`
- Main app: `main.py`
- Auth routes: `src/auth/oauth.py`
