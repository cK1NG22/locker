# cli/

`locker deploy` command. Thin wrapper over the vault API. (See ADR-0003)

## Purpose
Allows technical admins to push skill files from the terminal into the encrypted vault
without a UI.

## Key files (to be created)
- `main.py` — Typer CLI app entrypoint (registered as `locker` in pyproject.toml)
- `deploy.py` — `locker deploy <skill-file>` implementation

## Rules
- Thin client only: read file, POST to vault `/skills` with admin auth header
- No business logic here — validation and encryption belong in the vault
- Depends on vault API being stable before building
- Tests go in `tests/test_cli.py`
