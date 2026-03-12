# Locker

## What this is
Enterprise middleware that injects encrypted proprietary skills into LLM calls, keeping firm IP invisible to employees.

## Repo map
- `proxy/` — FastAPI proxy server; intercepts requests, injects skills, filters responses
- `vault/` — Encrypted skill storage (Postgres); admin-only access
- `src/auth/` — Admin auth and role-based access control
- `cli/` — `locker deploy` CLI; pushes skill files into the vault (see ADR-0003)
- `web/` — Next.js + Tailwind frontend (deployed on Vercel)
- `dashboard/` — ARCHIVED (replaced by `web/`; do not modify)
- `tests/` — pytest test suite
- `docs/decisions/` — Architecture Decision Records

## Rules
- Use Python for backend (FastAPI), React + Tailwind for frontend
- Package with Docker for on-prem deployment
- Encryption at rest: AES-256 via Python `cryptography` library
- Skills are never returned raw to non-admin users — always filter before responding
- Run tests before committing: `pytest`

## TODOs
- [ ] Create `src/auth/CLAUDE.md` stub (blocked by hook — needs user confirmation)
- [ ] Phase 3: Plan business-user feedback loop for skills (read-only users who want to suggest refinements to skills they can't edit — design UX and data model)
- [ ] Set up PostHog (product analytics)

## Commit discipline
- One commit = one logical change. If the commit message needs "and", split into two commits.
- Never combine feature work with bug fixes in a single commit.
- Run `pytest tests/ -x -q` before committing (pre-commit hook enforces this for Python files).

## Frontend
- The active frontend is `web/` (Next.js, deployed on Vercel).
- Do NOT modify files in `dashboard/`. It is archived.
- All UI work goes in `web/`.

## Sharp edges (create nested CLAUDE.md before editing these)
- `src/auth/` — breaks admin access if misconfigured
- `vault/` — skill leakage or data loss if mishandled
- `proxy/` — bugs here can expose firm IP to employees
