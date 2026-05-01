# Existing Supabase Patterns — Investigation Results

## Summary
No Supabase-using repositories exist in Carter's Projects directory. The primary codebase (`~/Projects/locker/`) uses PostgreSQL with Alembic migrations and plain asyncpg instead of Supabase. This is an opportunity to build Supabase alignment cleanly without legacy constraints.

---

## Locker v1 (Primary Codebase)

**Repo:** `~/Projects/locker/`  
**Status:** Live production system (Phase 3+ shipped)  
**DB Layer:** PostgreSQL (Railway-hosted)

### Schema Management
- **Tool:** Alembic (Python migration framework)
- **Migration location:** `migrations/versions/`
- **Convention:** Sequential numbered migrations (e.g. `001_initial_schema.py`, `002_add_audit_logs.py`)
- **Approach:** SQLAlchemy ORM definitions (not raw SQL) in downgrade/upgrade functions
- **Key observation:** Migrations are written directly in Python with `op.create_table()` calls; no raw `.sql` files

### Auth Pattern
- **User model:** `users` table with `id` (TEXT PK), `email`, `name`, `google_id` (unique)
- **Google OAuth 2.0:** Google Cloud OAuth, JWT token signing (HS256)
- **JWT handling:** 24-hour expiry, stored in cookies; `LOCKER_JWT_SECRET` env var controls signing
- **Service users:** 
  - **Team tokens:** Bearer tokens with `x-team-token` header, prefix-hashed in DB
  - **Personal access tokens:** Per-user tokens via `user_tokens` table (`token_hash`, `token_prefix`, `revoked_at`)
  - **API-key fallback:** `LOCKER_API_KEY` env var for admin routes (HMAC-verified)
- **No RLS enforcement:** Permission checks are application-layer (in FastAPI handlers), not database-level policies

### Permission/Authorization
- **Model:** Role-based (team/org member with `role` field: "member", "admin", etc.)
- **Enforcement:** FastAPI dependency injectors (`require_user`, `_require_org_member`, `_require_org_admin`)
- **No RLS:** All access control is in application code (routes check ownership before executing queries)
- **Cross-cutting:** Team membership enforced via join query on `team_members` table

### Data Model Highlights
- **Organizations:** Multi-tenant via `organizations` + `org_members` tables
- **Teams:** Have `name`, `slug`, `token_hash`, `invite_code`, `owner_id`, optional `org_id`
- **Skills:** Encrypted at rest (stored as TEXT, decrypted in-app), tagged with visibility (`open`/`shared`/`hidden`)
- **Audit logs:** `audit_logs` table tracks actions with `actor_id`, `action`, `resource_type`, `resource_id`, `metadata` (JSONB)

### Environment Variables
```
DATABASE_URL=postgresql://user:pass@host:port/locker
LOCKER_JWT_SECRET=<HS256 signing key>
LOCKER_ENCRYPTION_KEY=<AES-256 key, base64>
GOOGLE_CLIENT_ID=<OAuth client ID>
ANTHROPIC_API_KEY=<API key>
LOCKER_API_KEY=<optional admin API key>
LOCKER_BASE_URL=https://locker.up.railway.app
```

**Secret management:** All secrets via environment variables (Railway's native env manager, likely `.env` locally)

### Sync Patterns
- **No DB→filesystem sync code found.** Locker stores encrypted skills in the `skills` + `skill_files` tables; consumption is API-driven (MCP protocol, not file-based).
- **No cron/scheduler precedent:** No background jobs or SessionStart hooks. Async FastAPI handles real-time delivery via SSE (MCP).
- **Usage tracking:** Real-time logging to `skill_usage` table on each invocation.

### Indexing & Performance
- UNIQUEs on email, google_id, team name; no explicit indexes mentioned beyond PK/FK constraints.

---

## Why No Supabase

Locker pre-dates common Supabase patterns in Carter's workflows. The system uses:
- Direct `asyncpg` pool (not Supabase's PostgreSQL proxy)
- Manual token generation (not Supabase Auth)
- In-app permission logic (not RLS policies)
- Railway-hosted Postgres (not Supabase-hosted)

This is **not a blocker for variant-01.** It simply means the new build can establish Supabase conventions without migrating legacy code.

---

## Recommendations for variant-01

1. **Adopt Supabase for DB + Auth** if the build requires managed PostgreSQL + Auth UI. Benefit: Supabase Auth handles MFA, rate limiting, session management out-of-box.
2. **Use Supabase RLS for permission model** instead of application-layer checks. Pattern: row-level policies keyed to `auth.uid()` and custom JWT claims.
3. **Reference Locker's table/role structure** for multi-tenant shape (organizations → teams → members).
4. **Env var convention:** Align with Supabase standard (`SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`) rather than Locker's custom set.
5. **Migrations:** Use Supabase CLI (`supabase migration new --name "..."`) or plain SQL files versioned in `/supabase/migrations/` alongside the repo, not Python-based Alembic.

---

## Conclusion

**No existing Supabase codebase to align with.** Build cleanly with Supabase best practices (RLS-first, managed auth, native migrations). Locker serves as a reference for multi-tenant/team structure and permission semantics, but the DB layer is orthogonal.

