# ADR-0003: CLI Push as Phase 1 Import Mechanism

**Date:** 2026-03-02
**Status:** Accepted

## Context
Technical admins author skills in private Git repos and need a way to load them into the Locker vault. We evaluated two import paths: manual file upload via the dashboard UI, or a CLI tool (`locker deploy`).

## Decision
CLI push only for Phase 1. Admins run `locker deploy <skill-file>` from the terminal to push skills into the encrypted vault via the backend API.

## Consequences
**Easier:**
- No import UI to build for Phase 1 — significant frontend work eliminated
- Workflow is native to technical users already working in a terminal
- Less code to maintain; backend API endpoint is the single import surface

**Harder:**
- Less visual — harder to demo to non-technical buyers without a screen recording or live terminal demo

## Migration trigger
Add manual import UI when a customer or prospect explicitly requests it. The backend API endpoint is already shared, so this is a small frontend addition at that point.

## Alternatives considered
**Manual import (dashboard file upload):** Adds a drag-and-drop or file picker UI to the dashboard. Rejected for Phase 1 because it adds frontend work with no confirmed need — can be added in a few hours once the backend exists.
