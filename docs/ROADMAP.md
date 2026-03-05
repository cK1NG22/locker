# Roadmap

## Phase 1 — Core Middleware (DONE)

- [x] **1.1: Vault with encryption**
  4 tables (skills, skill_files, teams, team_skills), AES-256 encryption, full CRUD, 12 routes.
  `blocked-by: none`

- [x] **1.2: Anthropic proxy**
  Injection, response filtering, reference file tool-use loop.
  `blocked-by: 1.1`

- [x] **1.3: Teams and employee endpoint**
  Team-token auth, read-only skill listing for employees.
  `blocked-by: 1.1`

- [x] **1.4: CLI deploy**
  Single file + folder deploy commands.
  `blocked-by: 1.1`

- [x] **1.5: MCP server**
  Token injection, skill registration with Claude Code.
  `blocked-by: 1.1`

- [x] **1.6: Dashboard scaffolding**
  React + Tailwind: auth, skill CRUD, team CRUD, sidebar, routing.
  `blocked-by: 1.1`

- [x] **1.7: Companion page scaffolding**
  React components: token setup, skill list.
  `blocked-by: 1.1`

- [x] **1.8: Multi-file skill storage**
  skill_files table, file CRUD API, deploy-folder, manifest injection, lazy-load ref handler.
  `blocked-by: 1.1, 1.2`

## Phase 2 — Adam's Use Case (Team Skill Sharing)

- [x] **2.1: Add visibility column to skills table**
  Add `visibility` column with values: `hidden` (invisible auto-inject, default), `shared` (name+desc only), `open` (full content visible). ALTER TABLE migration, update vault CRUD, update models. Default `hidden` for backward compat.
  Files: `vault/db.py`, `vault/models.py`, `vault/routes.py`, `vault/employee_routes.py`
  Tests: update all existing tests for new field.
  `blocked-by: none`

- [x] **2.2: Update employee endpoint to respect visibility**
  `GET /api/v1/employee/skills` returns: full content for `open` skills, name+desc for `shared`, nothing for `hidden`. Update response serialization logic.
  Files: `vault/employee_routes.py`, `tests/test_employee.py`
  `blocked-by: 2.1`

- [x] **2.3: Upgrade companion page for open skills**
  Show full skill content for `open` skills with syntax highlighting or formatted markdown. Add copy-to-clipboard for `/locker <name>`. Visibility-aware rendering (hide content for `shared`, show badge).
  Files: `companion/src/components/SkillList.tsx`, `companion/src/components/SkillItem.tsx`, `companion/src/hooks/useSkills.ts`
  `blocked-by: 2.2`

- [x] **2.4: Add locker sync CLI command**
  New CLI command: pulls `shared`/`open` skills from vault via employee API (team token auth), writes .md files to `~/.claude/commands/`. Overwrites on re-sync. Clear output showing what was synced.
  Files: `cli/main.py`, new `cli/sync.py`, `tests/test_cli.py`
  `blocked-by: 2.2`

- [x] **2.5: Add list_skills MCP tool**
  Existing TODO. Returns skill names + descriptions from vault so Claude Code can suggest available skills to the user. Add to MCP server tool registry.
  Files: `locker_mcp/server.py`, `tests/test_mcp.py`
  `blocked-by: none`

- [x] **2.5b: Add fetch_skill MCP tool**
  Returns full content of an `open` skill by name. Powers the `/locker` thin router — Claude fetches skill content from the server at runtime instead of needing local .md files.
  Files: `locker_mcp/server.py`
  `blocked-by: 2.5`

- [x] **2.5c: Server-stored skills dogfood**
  `/locker` thin router skill deployed to vault. 3 skills (deploy/sync/e2e) stored on server, team "dogfood". Proves skills don't need local `.md` files. GitHub repo for the router skill: https://github.com/ck22coding/locker-skill
  `blocked-by: 2.5b`

- [x] **2.8: SSE MCP endpoint**
  `/mcp` SSE endpoint added to FastAPI server so remote users can connect without a local Python install. Uses Python `contextvars` to pass team token per connection. Adam's config: `{"type":"sse","url":"<host>/mcp","headers":{"X-Team-Token":"<token>"}}`.
  Files: `locker_mcp/sse_server.py`, `main.py`
  `blocked-by: none`

- [x] **2.6: Usage tracking**
  `skill_usage` table, `vault/usage.py` with log + admin endpoints (`GET /api/v1/usage`, `/usage/summary`). Proxy and MCP tools log invocations.
  Files: `vault/usage.py`, `vault/db.py`, `main.py`, `proxy/routes.py`, `locker_mcp/sse_server.py`
  `blocked-by: none`

- [x] **2.7: Feedback / refine**
  `skill_feedback` table, `vault/feedback.py` with team-token POST and admin GET/PATCH. `submit_feedback` MCP tool added.
  Files: `vault/feedback.py`, `vault/db.py`, `main.py`, `locker_mcp/sse_server.py`
  `blocked-by: 2.6`

- [x] **2.9a: Default skill visibility to open**
  Default changed from `hidden` to `open` in models and DB. `--visibility/-v` flag added to `locker deploy` CLI.
  Files: `vault/models.py`, `vault/db.py`, `cli/main.py`, `cli/deploy.py`
  `blocked-by: none`

- [x] **2.9b: Zero-friction onboarding: auto MCP config**
  `locker setup` CLI command writes MCP entry to `~/.claude.json` automatically. `--url` and `--token` flags.
  Files: `cli/main.py`, `cli/setup.py`
  `blocked-by: none`

- [x] **2.9c: Zero-friction onboarding: invite-based access**
  Dashboard "Invite Member" section with copy-to-clipboard link. Companion page auto-fills token from `?join=` URL param.
  Files: `dashboard/src/components/teams/TeamDetail.tsx`, `companion/src/App.tsx`, `companion/src/components/TokenSetup.tsx`
  `blocked-by: none`

- [x] **2.10: Zero-friction onboarding: auto skill download**
  `locker setup` also downloads `locker.md` from GitHub to `~/.claude/commands/`. One command = MCP config + skill install.
  Files: `cli/setup.py`
  `blocked-by: 2.9b`

## Phase 3 — Multi-Admin Skill Sharing

Two supported use cases, both possible within the same team:
- **Use case A (locked IP):** Team admin uploads skills, members consume them invisibly
- **Use case B (open sharing):** Members with `can_share` permission upload and share skills freely

- [x] **3.1: User accounts + Google OAuth**
  `users` table (id, email, name, google_id, created_at). Google OAuth login/signup flow. Session or JWT management. Replaces the current single global API key with real user identity.
  Files: `src/auth/`, `vault/db.py`, `main.py`, `dashboard/`
  `blocked-by: none`

- [x] **3.2: Team ownership model**
  Add `owner_id` to teams table. New `team_members` table: (team_id, user_id, role: admin|member, can_share: bool). Team creator is auto-assigned as admin. Migrate existing teams.
  Files: `vault/db.py`, `vault/models.py`, `vault/routes.py`
  `blocked-by: 3.1`

- [ ] **3.3: Per-member skill permissions**
  `can_share` toggle on team membership controls whether a member can upload skills to the team. Team admin can flip this per member from the dashboard. Members without `can_share` remain read-only.
  Files: `vault/routes.py`, `dashboard/src/components/teams/`
  `blocked-by: 3.2`

- [ ] **3.4: Skill ownership**
  Add `uploaded_by` (user_id) to skills table. Skills have a `scope`: personal (visible only to uploader) or team. Skill cards in dashboard show who uploaded them.
  Files: `vault/db.py`, `vault/models.py`, `vault/routes.py`, `dashboard/`
  `blocked-by: 3.1`

- [ ] **3.5: Cross-team skill copy**
  Members can share a skill into another team they belong to, creating an independent copy. Eligible skills: their own personal skills, or `open`-visibility team skills. Skills shared this way are owned by the sharer in the target team.
  Files: `vault/routes.py`, `dashboard/`
  `blocked-by: 3.3, 3.4`

- [ ] **3.6: Dashboard + UI updates**
  Sign up / login screens (Google OAuth). Team management UI: invite members, set role, toggle `can_share`. Skill cards show uploader name. Share-to-team action on eligible skills.
  Files: `dashboard/src/`
  `blocked-by: 3.5`
