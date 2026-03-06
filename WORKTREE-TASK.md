# Worktree Task: 4.2 — CI/CD pipeline (GitHub Actions)

## Task ID
4.2

## Branch
`dung/4.2-cicd-pipeline`

## Description
Add a GitHub Actions workflow that runs `pytest` on every push/PR against a Postgres service container. Include `ruff` for linting. Build the Docker image in CI to catch Dockerfile breakage.

## Files to Create/Modify
- New `.github/workflows/ci.yml`
- `pyproject.toml` (dev deps)

## Dependencies (all complete)
- 4.1: PostgreSQL migration — DONE (asyncpg, testcontainers, Alembic)

## Downstream Tasks (blocked by this task)
- 4.9: Production deployment (also needs this task complete)

## Key Context
- Tests use `testcontainers[postgres]` — CI needs Docker-in-Docker or a Postgres service container
- 171 tests currently passing
- DB is PostgreSQL via asyncpg (`vault/db.py`)
- `pyproject.toml` has all deps; tests run with `pytest`
- Dockerfile exists at project root

## Project References
- Project CLAUDE.md: `../../CLAUDE.md` (from project root)
- Roadmap: `docs/ROADMAP.md`
- Test suite: `tests/` directory (9 test files + conftest.py)
