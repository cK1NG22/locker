# Locker MVP Specification

## User Stories (MoSCoW Prioritization)

### Must Have
1. **As an admin**, I can deploy a skill (name, content, description) so that it appears in the vault with a visibility setting (hidden / shared / open).
2. **As a team member**, I can browse my team's skills so that I see only skills matching my access level and team assignment.
3. **As a team member**, I can call a skill via Claude Code's MCP integration (`/locker <skill-name>`) so that the skill content is injected into my conversation without leaving the terminal.

### Should Have
4. **As an admin**, I can view usage analytics so that I see call counts per skill, broken down by time period and team.

### Could Have
5. **As a team member**, I can submit structured feedback on a skill so that the admin sees a feedback queue with status tracking (pending / reviewed / resolved).

---

## Functional Requirements

### Authentication & Authorization
- Google OAuth 2.0 sign-in (no password management)
- JWT-based session tokens for dashboard access
- Team tokens (hashed, prefix-visible) for MCP authentication
- Personal access tokens for individual MCP connections
- Invite codes for frictionless team onboarding

### Skill Management (CRUD)
- Create skills with name, content, optional description
- Set visibility: **hidden** (admin-only), **shared** (team members see metadata), **open** (full access)
- Set scope: **personal** or **team**
- Update skill content and metadata
- Delete skills (cascades to files, usage, feedback)
- Attach supplementary files to skills (multi-file skill folders)

### Team Access Control
- Create teams with auto-generated slugs and invite codes
- Join teams via invite link (Google sign-in → auto-join)
- Role-based access: **owner**, **admin**, **member**
- Assign skills to teams via team_skills junction table
- Cross-team skill sharing via share requests (request → approve/deny)

### MCP Endpoint
- SSE transport at `/mcp` (legacy) and `/mcp/v2` (OAuth 2.1)
- `list_skills` tool — returns skill names and descriptions for the authenticated team
- `fetch_skill` tool — returns full skill content by name
- `submit_feedback` tool — records structured feedback on a skill
- `use_skill` tool — internal proxy for skill execution
- OAuth 2.1 with PKCE support on `/mcp/v2`

### Deployment
- Backend live at `https://locker.up.railway.app`
- Frontend live at `https://locker-ui-three.vercel.app`
- PostgreSQL database on Railway
- Health check at `/health` returns `{"status": "ok", "phase": 3}`

---

## Success Metrics
- **Signup-to-skill-call < 3 minutes** — New user can go from invite link to calling a skill in Claude Code in under 3 minutes
- **Data persistence** — Skills, usage logs, and feedback survive server restarts (PostgreSQL, not in-memory)
- **Test coverage** — 238+ automated tests passing (`pytest`)
- **Zero-downtime deploys** — Railway handles rolling deploys; no manual intervention needed

---

## Database Schema

### Core Tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `users` | Registered users | id, email, name, google_id, created_at |
| `skills` | Skill content store | id, name, content, description, visibility, scope, uploaded_by, created_at, updated_at |
| `teams` | Team groupings | id, name, slug, token_hash, token_prefix, token_encrypted, invite_code, owner_id, org_id, created_at |
| `team_members` | Team membership | id, team_id, user_id, role, can_share, created_at |
| `team_skills` | Skill-to-team assignments | team_id, skill_id (composite PK) |
| `skill_files` | Supplementary skill files | id, skill_id, path, content, size_bytes, created_at |
| `skill_usage` | Usage analytics | id, skill_name, team_id, invoked_at, source |
| `skill_feedback` | Structured feedback | id, skill_id, team_id, feedback_text, status, submitter_team_name, created_at |

### Auth & Organization Tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `organizations` | Multi-team orgs | id, name, slug, owner_id, skill_convention, created_at |
| `org_members` | Org membership | id, org_id, user_id, role |
| `user_tokens` | Personal access tokens | id, user_id, token_hash, token_prefix, name, created_at, revoked_at |
| `skill_share_requests` | Cross-team sharing | id, skill_id, from_team_id, to_team_id, requested_by, status, created_at |
| `audit_logs` | Activity audit trail | id, actor_id, action, resource_type, resource_id, metadata, created_at |
| `oauth_clients` | OAuth 2.1 clients | client_id, client_secret_hash, client_info_json, created_at |
| `oauth_codes` | OAuth authorization codes | code, client_id, user_id, team_id, scopes, code_challenge, redirect_uri, expires_at |
| `oauth_tokens` | OAuth access/refresh tokens | token_hash, token_type, client_id, user_id, team_id, scopes, expires_at, revoked |

---

## Out of Scope (MVP)
- **Multi-model proxy** — OpenAI/Gemini skill translation (Phase 4)
- **Skill marketplace** — Public skill discovery and distribution
- **Multi-org hierarchy** — Nested org structures beyond org → teams
- **SAML/SSO** — Enterprise SSO federation (Google OAuth only for MVP)
- **Mobile app** — No mobile use case for developer tool
- **Injection scanning** — Automated prompt injection detection in skill content
- **AGENTS.md export** — Cross-tool format translation (Phase 3.8+)
