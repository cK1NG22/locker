# vault/

Encrypted skill storage. The data layer everything else depends on.

## Purpose
Stores proprietary skills encrypted at rest (AES-256). Exposes admin-only CRUD API
consumed by the proxy (reads skills) and the CLI/dashboard (writes skills).

## Key files
- `db.py` — PostgreSQL connection via asyncpg
- `models.py` — Pydantic data models
- `crypto.py` — AES-256 encrypt/decrypt helpers
- `routes.py` — FastAPI CRUD endpoints for skills (`POST /skills`, `GET /skills/{id}`, etc.)

## Rules
- Skill content MUST be encrypted at rest (AES-256 via `cryptography` lib)
- All write routes require admin auth from `src/auth/`
- Database: PostgreSQL via asyncpg (hosted on Railway)
- Tests go in `tests/test_vault.py`
