# Worktree Task: 4.3 — Self-serve team creation + onboarding wizard

## Task ID
4.3

## Branch
`dung/4.3-self-serve-team-creation`

## Description
Add a "Create Team" flow to the dashboard so any logged-in user can create a team, get a token, and see setup instructions — all without CLI or API calls. Include a "Getting Started" wizard: create team -> upload first skill -> invite first member.

## Files to Create/Modify
- `dashboard/src/` (new pages/components)

## Dependencies (all complete)
- None

## Downstream Tasks (blocked by this task)
- 4.7: Dashboard analytics page

## Key Context
- Dashboard is React + Tailwind (`dashboard/` directory)
- Team creation API already exists: `POST /api/v1/teams`
- Auth uses Google OAuth with JWT tokens
- Admin routes require `Authorization: Bearer <jwt>`
- Teams have tokens for employee access (X-Team-Token header)
- Existing team management UI in `dashboard/src/components/teams/`

## Project References
- Project CLAUDE.md: `../../CLAUDE.md` (from project root)
- Roadmap: `docs/ROADMAP.md`
- Dashboard: `dashboard/` directory
- Team routes: `vault/team_routes.py`
