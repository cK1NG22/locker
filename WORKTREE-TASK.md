# Worktree Task: 3.1 — User Accounts + Google OAuth

## Branch
`dung/3.1-user-accounts-google-oauth`

## Task Description
Add real user accounts and Google OAuth login/signup to Locker. This replaces the current single global API key admin model with individual user identities.

Specifically:
- `users` table: id, email, name, google_id, created_at
- Google OAuth login/signup flow (Google is the provider)
- Session or JWT management (JWT preferred — evaluate and decide)
- The current single `X-API-Key` global admin auth must coexist during transition OR be fully replaced — evaluate the migration path carefully
- Dashboard must get a login/signup screen powered by OAuth
- Any route currently protected by `X-API-Key` needs to be updated to use user identity

Files likely affected: `src/auth/`, `vault/db.py`, `main.py`, `dashboard/`

## Dependencies (all complete)
None — this is the foundation task.

## Downstream Impact
These tasks are waiting on this one:
- **3.2: Team ownership model** — needs user IDs to assign team owners and populate team_members
- **3.4: Skill ownership** — needs user IDs to track who uploaded each skill

## Project Context
- Project CLAUDE.md: `../CLAUDE.md` (relative to worktree root = repo root)
- Full roadmap: `../docs/ROADMAP.md`
- Auth directory (sharp edge — read CLAUDE.md warning): `../src/auth/`

## Key Decisions Already Made
- OAuth provider: Google
- Cross-team skill sharing uses copy (not live links)
- Team creator = team admin
- Per-member `can_share` toggle controls upload permissions

## Instructions
1. Read this file to understand your task scope.
2. Read `../docs/ROADMAP.md` Phase 3 section for full context.
3. Read `../src/auth/` carefully — this is a sharp edge per CLAUDE.md.
4. Run `/opusplan` to create a detailed implementation plan.
5. Get user approval on the plan before building anything.
6. When done, commit your changes to this branch.

## Cleanup
When this task is complete:
1. Mark task `3.1` as `[x]` in `../docs/ROADMAP.md`
2. From the main repo run: `git worktree remove .claude/worktrees/dung/3.1-user-accounts-google-oauth`
