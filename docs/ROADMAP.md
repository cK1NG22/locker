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

- [x] **3.3: Per-member skill permissions**
  `can_share` toggle on team membership controls whether a member can upload skills to the team. Team admin can flip this per member from the dashboard. Members without `can_share` remain read-only.
  Files: `vault/routes.py`, `dashboard/src/components/teams/`
  `blocked-by: 3.2`

- [x] **3.4: Skill ownership**
  Add `uploaded_by` (user_id) to skills table. Skills have a `scope`: personal (visible only to uploader) or team. Skill cards in dashboard show who uploaded them.
  Files: `vault/db.py`, `vault/models.py`, `vault/routes.py`, `dashboard/`
  `blocked-by: 3.1`

- [x] **3.5: Cross-team skill copy**
  Members can share a skill into another team they belong to, creating an independent copy. Eligible skills: their own personal skills, or `open`-visibility team skills. Skills shared this way are owned by the sharer in the target team.
  Files: `vault/routes.py`, `dashboard/`
  `blocked-by: 3.3, 3.4`

- [x] **3.6: Dashboard + UI updates**
  Sign up / login screens (Google OAuth). Team management UI: invite members, set role, toggle `can_share`. Skill cards show uploader name. Share-to-team action on eligible skills.
  Files: `dashboard/src/`
  `blocked-by: 3.5`

## Phase 4 — Production-Ready (Scale, Safety, Onboarding)

- [x] **4.1: PostgreSQL migration (Postgres-only)**
  Replace SQLite entirely with Postgres via `asyncpg`. Rewrite `vault/db.py` to use asyncpg connection pool, update all raw SQL to Postgres syntax (`$1` params instead of `?`). Add `DATABASE_URL` env var. Add Alembic for schema migrations. Update Dockerfile to remove SQLite deps. Update test fixtures to use a test Postgres DB.
  Files: `vault/db.py`, `pyproject.toml`, new `alembic/` dir, `Dockerfile`, `.env.example`, all test files (fixture update)
  `blocked-by: none`

- [ ] **4.2: CI/CD pipeline (GitHub Actions)**
  Add a GitHub Actions workflow that runs `pytest` on every push/PR against a Postgres service container. Include `ruff` for linting. Build the Docker image in CI to catch Dockerfile breakage.
  Files: new `.github/workflows/ci.yml`, `pyproject.toml` (dev deps)
  `blocked-by: 4.1`

- [x] **4.3: Self-serve team creation + onboarding wizard**
  Add a "Create Team" flow to the dashboard so any logged-in user can create a team, get a token, and see setup instructions — all without CLI or API calls. Include a "Getting Started" wizard: create team -> upload first skill -> invite first member.
  Files: `dashboard/src/` (new pages/components)
  `blocked-by: none`

- [ ] **4.4: Hashed team tokens + rotation**
  Hash team tokens at rest (SHA-256 + salt). Store a `token_prefix` (first 8 chars) for display in the dashboard. Add `POST /api/v1/teams/{id}/rotate-token` endpoint. Full token shown exactly once on creation/rotation.
  Files: `vault/db.py` (migration), `vault/team_routes.py`, `vault/employee_routes.py`, `locker_mcp/sse_server.py`
  `blocked-by: 4.1`

- [ ] **4.5: Rate limiting**
  Add per-IP and per-token rate limiting via `slowapi` middleware. Key limits: employee endpoints (60 req/min per token), admin endpoints (120 req/min per user), auth endpoint (10 req/min per IP). Log rate-limit hits.
  Files: `main.py`, `pyproject.toml`, new `src/middleware/rate_limit.py`
  `blocked-by: none`

- [ ] **4.6: Audit logging**
  New `audit_log` table tracking: skill CRUD, team CRUD, member changes, token rotations, logins. Columns: `id, actor_id, action, resource_type, resource_id, metadata (JSON), created_at`. Admin endpoint `GET /api/v1/audit-log` with filters. Lightweight helper function so route files just call `await audit(...)`.
  Files: `vault/db.py`, new `vault/audit.py`, touch route files for audit calls, `main.py`
  `blocked-by: 4.1`

- [ ] **4.7: Dashboard analytics page**
  Visualize the usage data already collected by `skill_usage` table. Show: skills ranked by usage, usage over time (daily chart), active teams, recent feedback. Mostly frontend — add one new backend endpoint `GET /api/v1/usage/timeseries` for chart data.
  Files: `dashboard/src/` (new Analytics page), `vault/usage.py`
  `blocked-by: 4.3`

- [ ] **4.8: Product analytics (PostHog)**
  NEEDS PLANNING. Integrate PostHog for tracking user behavior: sign-ups, feature adoption, funnels, retention. Separate from security audit logging (4.6) and admin-facing usage analytics (4.7).
  `blocked-by: none`

- [ ] **4.9: Production deployment**
  NEEDS PLANNING. Docker production config, cloud provider setup, domain + SSL, environment management, health checks, backup strategy.
  `blocked-by: 4.1, 4.2`

## Phase 5 — Billing & Monetization

Per-team billing via Stripe. Free forever for now — build the infrastructure, flip the switch later.

- [ ] **5.1: Billing data model + Alembic migration**
  Three new tables: `plans` (slug, name, price_cents, stripe_price_id, limits JSONB), `subscriptions` (team_id, plan_id, status, stripe_customer_id, stripe_subscription_id, period dates), `usage_meters` (team_id, metric, value, period dates). JSONB for plan limits = add new billable dimensions without migrations.
  Files: new `alembic/versions/xxxx_add_billing_tables.py`, new `vault/billing_models.py`
  `blocked-by: 4.1`

- [ ] **5.2: Stripe integration service**
  Thin wrapper around Stripe Python SDK: `create_customer`, `create_checkout_session` (hosted page), `create_portal_session` (subscription management), `handle_webhook`. Stripe Checkout = zero payment UI to build. Stripe Customer Portal = zero subscription management UI.
  Files: new `vault/stripe_service.py`, `pyproject.toml` (+stripe), `.env.example`
  `blocked-by: 5.1`

- [ ] **5.3: Billing API endpoints**
  Six routes: `GET /billing/plans`, `GET /billing/team/{id}/subscription`, `POST /billing/team/{id}/checkout`, `POST /billing/team/{id}/portal`, `GET /billing/team/{id}/usage`, `POST /billing/webhooks`. Webhook events: checkout.session.completed, subscription.updated/deleted, invoice.payment_succeeded/failed. App works without Stripe env vars — billing endpoints return 503 if unconfigured.
  Files: new `vault/billing_routes.py`, `main.py`
  `blocked-by: 5.1, 5.2, 5.4`

- [ ] **5.4: Usage metering infrastructure**
  Billing-oriented aggregation on top of existing `skill_usage` table. Helper functions: `record_meter(team_id, metric, value, mode)`, `get_current_usage(team_id)`. Metrics: member_count (snapshot), skill_invocations (increment), skills_count (snapshot).
  Files: new `vault/metering.py`, `vault/usage.py`, `vault/team_routes.py`
  `blocked-by: 5.1`

- [ ] **5.5: Seed plans + auto-provision free tier**
  On startup, ensure plans table has Free + Pro rows (idempotent). On team creation, auto-create free subscription. Backfill existing teams on first billing API call. No Stripe objects for free-only teams.
  Files: new `vault/billing_seed.py`, `main.py`, `vault/team_routes.py`
  `blocked-by: 5.1, 5.2`

- [ ] **5.6: Dashboard billing page**
  Per-team page showing: current plan, usage summary (members, skills, invocations), upgrade button (→ Stripe Checkout), manage subscription button (→ Stripe Portal). No upgrade nags elsewhere. Usage bars show values without thresholds (limits not enforced yet).
  Files: new `dashboard/src/components/billing/BillingPage.tsx`, new `dashboard/src/hooks/useBilling.ts`, `App.tsx`, `Sidebar.tsx`
  `blocked-by: 5.3`

- [ ] **5.7: Marketing site / landing page**
  NEEDS PLANNING. Public-facing website explaining Locker, driving sign-ups.
  `blocked-by: 4.9`

## Phase 6 — Skill Versioning

- [ ] **6.1: Skill versioning + maintenance workflow**
  NEEDS PLANNING. Skill edit history, version snapshots, how edits propagate to users who have synced a skill locally (`locker sync`), how cross-team copies handle upstream edits, and whether there's a "refresh" mechanic. Admin workflow for iterating on a skill over time without breaking existing users.
  `blocked-by: 3.6`

## Phase 7 — Firm Context + Security

- [ ] **7.1: Firm context data model**
  NEEDS PLANNING. Central repo for firm knowledge. `context_sources` table, `skill_context_sources` link table. Static context first, live queries later.
  `blocked-by: 4.1`

- [ ] **7.2: Layered access control**
  NEEDS PLANNING. Firm admin sets broad data-access policies, Skill Orchestrators restrict further (never expand). File-level access.
  `blocked-by: 7.1`

- [ ] **7.3: Dependency checking + blocked access**
  NEEDS PLANNING. Check employee clearance against all skill data dependencies before granting access. Block skill + request-access flow.
  `blocked-by: 7.2`

- [ ] **7.4: Permission Sandwich**
  NEEDS PLANNING. Pre-call permission gate (only authorized data in prompt) + post-call response filter (scan output for leaks). Both layers always active.
  `blocked-by: 7.3`

- [ ] **7.5: Context transparency UI**
  NEEDS PLANNING. Employees see which context sources a skill draws from (names/labels only, not content).
  `blocked-by: 7.1`

## Phase 8 — Connectors: Cloud Integrations

- [ ] **8.1: Connector permission layer**
  NEEDS PLANNING. Locker acts as permission/routing layer on Claude-native integrations (Google Drive, Slack, etc.). Skills declare data needs, Locker routes to right connector.
  `blocked-by: 7.2`

- [ ] **8.2: Connector setup wizard**
  NEEDS PLANNING. Guided UI for firm admins to provision connectors and set access policies. Skill Orchestrators link approved connectors to skills.
  `blocked-by: 8.1`

- [ ] **8.3: Graceful degradation**
  NEEDS PLANNING. If connector is down, skill runs with available data. Employee gets brief note, admin gets detailed diagnostics.
  `blocked-by: 8.1`

## Phase 9 — Credentials Vault

- [ ] **9.1: Vault data model**
  NEEDS PLANNING. Unified encrypted vault (AES-256). Firm-level creds (admin-managed) + personal creds (employee-managed). Shared with Connectors for API keys/DB passwords.
  `blocked-by: 8.1`

- [ ] **9.2: Proxy injection mechanism**
  NEEDS PLANNING. Locker intercepts credential requests, injects from vault, agent sees only result. LLM never has sensitive values in context.
  `blocked-by: 9.1`

- [ ] **9.3: Credential onboarding UI**
  NEEDS PLANNING. Employee self-service for entering/managing credentials. Enterprise tier adds admin provisioning later.
  `blocked-by: 9.2`

## Phase 10 — Connectors: Native / On-Prem

- [ ] **10.1: Locker-native connectors**
  NEEDS PLANNING. For systems Claude doesn't support (on-prem databases, internal APIs, niche CRMs). Same permission model as Phase 8.
  `blocked-by: 8.1`

- [ ] **10.2: On-prem data access**
  NEEDS PLANNING. Locker deployed inside firm infrastructure, reaches internal servers. Firm data never leaves their network.
  `blocked-by: 10.1`

## Phase 11 — Skills Marketplace

- [ ] **11.1: Output skill packaging**
  NEEDS PLANNING. Transform process skills into output skills (input → result, no methodology exposed).
  `blocked-by: 5.6, 9.1`

- [ ] **11.2: Marketplace vetting + listing**
  NEEDS PLANNING. Snyk-style automated scanning + Locker review. Open to firms, Skill Orchestrators, freelancers.
  `blocked-by: 11.1`

- [ ] **11.3: Marketplace pricing + revenue**
  NEEDS PLANNING. Seller sets price (per-execution or subscription). Locker takes platform fee. Free skills allowed.
  `blocked-by: 11.2`

- [ ] **11.4: IP protection**
  NEEDS PLANNING. Output-only model, encryption-at-rest foundation, obfuscated output.
  `blocked-by: 11.1`
