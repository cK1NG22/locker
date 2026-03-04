# vault/

Encrypted skill storage. The data layer everything else depends on.

## Purpose
Stores proprietary skills encrypted at rest (AES-256). Exposes admin-only CRUD API
consumed by the proxy (reads skills) and the CLI/dashboard (writes skills).

## Key files (to be created)
- `db.py` — DB connection and session management
- `models.py` — SQLite schema and data models
- `crypto.py` — AES-256 encrypt/decrypt helpers
- `routes.py` — FastAPI CRUD endpoints for skills (`POST /skills`, `GET /skills/{id}`, etc.)

## Rules
- Skill content MUST be encrypted at rest (AES-256 via `cryptography` lib)
- All write routes require admin auth from `src/auth/`
- SQLite for Phase 1; migrate to PostgreSQL when multi-admin or multi-node (see ADR-0002)
- Write clean ANSI SQL from day one — no SQLite-specific syntax
- Tests go in `tests/test_vault.py`
