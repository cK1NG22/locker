# Locker

## What this is
Enterprise middleware that injects encrypted proprietary skills into LLM calls, keeping firm IP invisible to employees.

## Repo map
- `proxy/` — FastAPI proxy server; intercepts requests, injects skills, filters responses
- `vault/` — Encrypted skill storage (Postgres); admin-only access
- `src/auth/` — Admin auth and role-based access control
- `cli/` — `locker deploy` CLI; pushes skill files into the vault (see ADR-0003)
- `dashboard/` — React + Tailwind admin UI for skill CRUD and team management
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

## Sharp edges (create nested CLAUDE.md before editing these)
- `src/auth/` — breaks admin access if misconfigured
- `vault/` — skill leakage or data loss if mishandled
- `proxy/` — bugs here can expose firm IP to employees
