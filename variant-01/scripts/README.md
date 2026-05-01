# Supabase COS Variant — Build Scripts

SQL migrations + Python helpers for the Supabase COS variant build (per ADRs `../docs/decisions/0001/0002/0003`, plan at `~/.claude/plans/dreamy-syncing-supabase.md`).

This directory was migrated from `~/Projects/mock-cos/scripts/` to `~/Projects/locker/variant-01/scripts/` on 2026-04-29 — the work belongs to Locker as variant-01 (storage-layer dogfood), not mock-cos (Notion COS comparison sandbox). See `../CLAUDE.md` for variant scope rules. All scripts target the live Supabase project Carter creates per Stage 0 below.

---

## Stage 0 — One-time setup (Carter does this, in the Supabase dashboard)

These steps need the Supabase web UI; Claude can't do them for you.

### 0.1 — Create the Supabase project

1. Go to https://supabase.com/dashboard and click **New Project**.
2. Settings:
   - **Name:** `optimal-cos` (or your preferred name)
   - **Database password:** generate a strong one and save in 1Password as `optimal-cos-db-password`
   - **Region:** closest to you (e.g., `us-west-1` or `us-east-1`)
3. Wait ~2 minutes for the project to provision.
4. Once it's up, go to **Project Settings → API** and copy:
   - **Project URL** → `SUPABASE_URL` in your `.env`
   - **`anon` `public` key** → `SUPABASE_ANON_KEY`
   - **`service_role` `secret` key** → `SUPABASE_SERVICE_ROLE_KEY` ⚠️ NEVER COMMIT THIS

### 0.2 — Create the `.env` file

```bash
cd ~/Projects/locker/variant-01/scripts
cp .env.example .env
chmod 600 .env
# Edit .env and paste the three keys + your email + a strong password for the agent
```

⚠️ The repo-root `.gitignore` already excludes `.env` — **but** `chmod 600` is a defense-in-depth so other shell users on this machine can't read it.

### 0.3 — Run the schema migration (`0001_schema.sql`)

In the Supabase dashboard:

1. Go to **SQL Editor → New Query**
2. Paste the entire contents of `0001_schema.sql`
3. Click **Run**. You should see *"Success. No rows returned."*
4. Verify by going to **Database → Tables**: you should see `public.teams` and `public.memberships`.

### 0.4 — Create the human owner user (Carter)

In the Supabase dashboard:

1. **Authentication → Users → Add user**
2. **Email:** matching `OPTIMAL_OWNER_EMAIL` in `.env` (e.g., `carter@get-optimal.ai`)
3. **Password:** matching `OPTIMAL_OWNER_PASSWORD`
4. ✅ **Auto Confirm User**
5. Click **Create user**

### 0.5 — Create the COS sync agent

In the Supabase dashboard:

1. **Authentication → Users → Add user**
2. **Email:** matching `COS_AGENT_EMAIL` (e.g., `cos-sync-agent@get-optimal.ai`)
3. **Password:** matching `COS_AGENT_PASSWORD`
4. ✅ **Auto Confirm User**
5. Click **Create user**

### 0.6 — Mark the agent as `app_metadata.role = 'agent'`

This is the principal-type claim that Stage 1's RLS uses to block agent writes. Supabase Studio doesn't have a direct UI for `app_metadata` (the *server-controlled* metadata, distinct from `user_metadata` which users can self-edit), so we set it via SQL:

In **SQL Editor → New Query**:

```sql
update auth.users
set raw_app_meta_data = raw_app_meta_data || '{"role": "agent"}'::jsonb
where email = 'cos-sync-agent@get-optimal.ai';
```

Run. Verify:

```sql
select email, raw_app_meta_data
from auth.users
where email = 'cos-sync-agent@get-optimal.ai';
```

The `raw_app_meta_data` column should include `"role": "agent"`. If it doesn't, Stage 1's verify script will catch it and tell you to come back here.

---

## Stage 1 — Seed and verify (run from your terminal)

### 1.1 — Install Python dependency

```bash
cd ~/Projects/locker/variant-01/scripts
python3 -m pip install supabase
```

### 1.2 — Seed the Optimal AI team + 2 memberships

```bash
python3 stage_1_seed.py
```

Expected:

```
Looking up users via admin API...
Ensuring team 'Optimal AI' (slug='optimal-ai')...
  Team created: id=<uuid>
Ensuring owner membership (carter@get-optimal.ai, role=owner)...
Ensuring agent membership (cos-sync-agent@get-optimal.ai, role=agent)...

=== Stage 1 seed complete ===
  Team:    Optimal AI (id=<uuid>)
  Owner:   carter@get-optimal.ai (uid=<uuid>)
  Agent:   cos-sync-agent@get-optimal.ai (uid=<uuid>, app_metadata.role=agent)

Next: run `python3 stage_1_verify.py` to confirm RLS policies work end-to-end.
```

The script is **idempotent** — re-running upserts the team by slug and memberships by composite key. Safe to run if anything went wrong.

### 1.3 — Verify RLS policies (the stop+review gate)

```bash
python3 stage_1_verify.py
```

Expected:

```
Stage 1 verify — RLS policy end-to-end check

Signing in as owner (Carter)...
Signing in as agent (cos-sync-agent)...

  [PASS] Test 1 — Owner can SELECT teams via membership  (rows=1)
  [PASS] Test 2 — Agent can SELECT teams via membership  (rows=1)
  [PASS] Test 3 — Owner can UPDATE teams (owner + not agent)  (affected=1)
  [PASS] Test 4 — Agent UPDATE teams silently filters (no rows affected)  (affected=0)
  [PASS] Test 5 — Agent INSERT memberships raises (RLS reject)  (code=42501)

=== 5/5 tests passed ===

Stage 1 stop+review gate: GREEN. You can proceed to Stage 2.
```

If anything fails (especially Test 4 or Test 5 — those are the ones that prove agents *cannot* mutate), do NOT proceed to Stage 2. The whole point of the substrate choice (per ADR-0001) is that the database physically rejects forbidden agent writes. If those tests fail, the schema is letting agents do something they shouldn't.

---

## Hard rules carried from `../CLAUDE.md` Supabase variant scope

- **Never use `service_role` from agents.** Agents always use scoped JWTs from `signInWithPassword`. Service-role belongs only to admin scripts running locally as Carter (this directory's seed scripts).
- **`.env` is gitignored.** Never commit. `chmod 600 .env` after creating.
- **Never paste production schemas, connection strings, service-role keys, or real client data into shared docs/Slack/PRs.**
- **Stage N+1 doesn't start until Stage N's verify passes.** The stop+review gates are not advisory.

---

## File layout

| File | Purpose |
|---|---|
| `0001_schema.sql` | Stage 1 schema migration (teams + memberships + RLS + SECURITY DEFINER helpers) |
| `stage_1_seed.py` | Stage 1 seed — creates Optimal AI team + 2 memberships (idempotent) |
| `stage_1_verify.py` | Stage 1 stop+review gate — 5 RLS tests, exits non-zero if any fail |
| `.env.example` | Env-var template — copy to `.env` and fill in |
| `.env` | **Gitignored.** Holds your real Supabase credentials. |

---

## What's next (after Stage 1 stop+review gate is green)

Stage 2 will add:
- `resources` table (with `type='connector'` for connectors — flatten per ADR-0003)
- RLS policies on `resources` (read via membership, write blocked for agents via `not is_agent()`)
- One seed row (Optimal AI's Company Info)
- Verify: agent can read it but not write it

Stage 3+: skills table, sync-on-disk script, `SessionStart` hook integration. See the plan for the full sequence.
