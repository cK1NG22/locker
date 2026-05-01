# Supabase Build — Technical Pattern Research

**Date:** 2026-04-27
**Scope:** Three patterns for the Supabase COS dogfood (per `~/.claude/plans/dreamy-syncing-supabase.md`)
**Status:** Reference; informs ADR-0001 (formerly mock-cos ADR-0008) and Stage 1–3 implementation

---

## L0 — Executive Summary

1. **Agent-as-Auth-user is the paved path.** Each agent gets a row in `auth.users`, signs in via `signInWithPassword`, and receives standard short-lived JWTs (default 1h access + single-use refresh that never expires). `app_metadata.role='agent'` is read in RLS via `auth.jwt() -> 'app_metadata' ->> 'role'`. Custom Access Token Hooks can copy that into a top-level claim if useful. Never use `service_role` from agents.
2. **RLS negative testing is mature on Supabase via pgTAP + the `basejump-supabase_test_helpers` extension.** `tests.authenticate_as()` sets JWT claims and Postgres role; `throws_ok(..., '42501', ...)` asserts inserts are rejected; `is_empty()` covers updates/deletes (which fail silently rather than throwing).
3. **`SessionStart` hook is well-documented and fits the sync use case.** Configured in `~/.claude/settings.json`, runs on every session start/resume, exposes `CLAUDE_PROJECT_DIR` and `CLAUDE_ENV_FILE`. Exit 0 = stdout joins context; exit 2 = blocking error to stderr. Keep it fast.

**Confidence:** High on Q1 and Q3 (official docs are explicit). High on Q2 (multiple worked examples). One gap flagged below: Python-client token-to-disk persistence requires a custom storage class — no first-party doc.

---

## L1 — Detailed Patterns

### Q1 — Agent JWT Pattern

**Principal model.** Production teams represent agents as ordinary `auth.users` rows distinguished by `app_metadata`. `app_metadata` is server-controlled (settable only by `service_role` or admin API), so RLS can trust it; `user_metadata` is user-writable and must not gate authorization. The role claim in the JWT itself ([`role`](https://supabase.com/docs/guides/auth/jwts)) must remain a Postgres role (`anon`, `authenticated`, `service_role`) — agents sign in as `authenticated` and carry their "agent-ness" in `app_metadata.role='agent'`.

**Token mint.** Standard `signInWithPassword` against the agent's Auth user yields an access token (default 1h, configurable; Supabase warns against >1h or <5m) and a refresh token. Refresh tokens never expire but are single-use, with a [10-second reuse window](https://supabase.com/docs/guides/auth/sessions) for retry safety. Out-of-window reuse revokes the entire session — protective against stolen tokens.

**Long-lived agent strategy.** Three options, in order of paved-path-ness:
1. **Auto-refresh in a long-running process.** `client.auth.startAutoRefresh()` (Node) or `auth.set_session(...)` then periodic `auth.refresh_session()` (Python). Persist `{access_token, refresh_token}` to disk between runs.
2. **Custom Access Token Hook** to extend exp or inject a stable `role` top-level claim. The [`custom_access_token_hook`](https://supabase.com/docs/guides/auth/auth-hooks/custom-access-token-hook) function runs on every issuance.
3. **Self-signed JWT with imported private key** via `supabase gen signing-key --algorithm ES256` — full control, but you own rotation. Avoid unless (1) and (2) don't fit.

**For the COS sync agent:** option 1 fits — short-lived script, refresh on each invocation. Token cache file at `~/.config/optimal-cos/agent.token` (per the plan) holds the refresh token; access token can be re-derived via `refresh_session` at start. Permission file 600.

**RLS reading the role.** In policies, use `((auth.jwt() -> 'app_metadata' ->> 'role') = 'agent')`. Or, for performance, copy `app_metadata.role` into a top-level claim via the Custom Access Token Hook and read `auth.jwt() ->> 'role'` (cheaper but conflicts with the Postgres-role `role` claim — name it `user_role` instead, per [Supabase RBAC docs](https://supabase.com/docs/guides/database/postgres/custom-claims-and-role-based-access-control-rbac)).

### Q2 — RLS Negative Testing

**Stack.** `pgtap` extension + `basejump-supabase_test_helpers` (community, but [linked from Supabase docs](https://supabase.com/docs/guides/local-development/testing/pgtap-extended)). Install:
```sql
create extension if not exists pgtap with schema extensions;
select dbdev.install('basejump-supabase_test_helpers');
create extension "basejump-supabase_test_helpers" version '0.0.6';
```

**Two failure modes to handle separately.**
- **INSERT** violating RLS raises Postgres error `42501` ("new row violates row-level security policy"). Test with `throws_ok()`.
- **UPDATE / DELETE / SELECT** violating RLS [silently filters](https://usebasejump.com/blog/testing-on-supabase-with-pgtap) — the row count just drops to zero. Test with `is_empty()` over a `RETURNING` clause.

**Impersonation.** Two equivalent paths:
1. `tests.authenticate_as('agent_alice')` — Basejump helper that sets JWT claims (`request.jwt.claim.sub`, `request.jwt.claims` JSON with `app_metadata`) and `set role authenticated`.
2. Manual: `set local role authenticated; select set_config('request.jwt.claims', '{"sub":"...","app_metadata":{"role":"agent"}}', true);` — works with raw `pgtap`, no extension.

**Pattern.** Wrap each test in `BEGIN; ... ROLLBACK;` so rows from failed-inserts and impersonation state never persist. Setup data with `tests.authenticate_as_service_role()`; assertions under the principal under test.

A worked agent-write-rejection example is in L2 below.

### Q3 — Claude Code SessionStart Hook

**Schema.** `~/.claude/settings.json` (or per-project `.claude/settings.json`):
```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup",
        "hooks": [
          { "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/scripts/sync-skills.py",
            "statusMessage": "Syncing skills from Supabase" }
        ]
      }
    ]
  }
}
```

**Triggers.** `matcher` selects the `source`: `startup` (new session), `resume` (`--resume`/`/resume`/`--continue`), `clear` (after `/clear`), `compact` (auto/manual compaction). Omit or `*` to match all.

**Env vars in scope.**
- `CLAUDE_PROJECT_DIR` — project root (always set).
- `CLAUDE_ENV_FILE` — path to a file the hook can append `export FOO=bar` lines to; those are loaded into the session env (SessionStart, CwdChanged, FileChanged only).
- `CLAUDE_CODE_REMOTE` — `"true"` in web/cloud envs, unset locally.
- Plus stdin JSON: `{session_id, transcript_path, cwd, hook_event_name, source, model}`.

**Failure surfacing.** Exit 0 = success; stdout becomes added context (or use the structured `{hookSpecificOutput: {hookEventName, additionalContext}}` JSON form). Exit 2 = blocking error; stderr fed back as error. Other non-zero = non-blocking; first stderr line shown in transcript, full stderr in debug log. Only `type: "command"` and `type: "mcp_tool"` are supported for SessionStart.

**Constraint.** Runs on *every* session-start event, including resume/clear/compact. Long-running fetches block session start. For the COS sync, either (a) gate to `matcher: "startup"` only, (b) keep total runtime under ~2s, or (c) fork-and-detach the heavy work and return immediately.

**Gap flagged.** Whether SessionStart hooks fire when a session is resumed via `claude -c` from a different cwd is not explicitly documented; the `cwd` field in the input is informational, but matcher selection is by `source`, not directory. Worth verifying empirically in Stage 3.

---

## L2 — Code Examples

### Q1 — Python agent sign-in with persisted refresh token

```python
# scripts/agent_auth.py
import json, os, pathlib
from supabase import create_client, Client

TOKEN_FILE = pathlib.Path.home() / ".config" / "optimal-cos" / "agent.token"
TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)

def get_client() -> Client:
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_ANON_KEY"])
    if TOKEN_FILE.exists():
        cached = json.loads(TOKEN_FILE.read_text())
        try:
            sb.auth.set_session(cached["access_token"], cached["refresh_token"])
            sb.auth.refresh_session()  # uses refresh token; rotates pair
        except Exception:
            _password_login(sb)
    else:
        _password_login(sb)
    s = sb.auth.get_session()
    TOKEN_FILE.write_text(json.dumps({
        "access_token": s.access_token, "refresh_token": s.refresh_token
    }))
    TOKEN_FILE.chmod(0o600)
    return sb

def _password_login(sb: Client):
    sb.auth.sign_in_with_password({
        "email": os.environ["AGENT_EMAIL"],
        "password": os.environ["AGENT_PASSWORD"],
    })
```

Set `app_metadata.role='agent'` once via the admin API (run by Carter, not the agent):
```sql
update auth.users
set raw_app_meta_data = raw_app_meta_data || '{"role":"agent"}'::jsonb
where email = 'cos-sync-agent@optimal.ai';
```

### Q2 — Negative RLS test: agent attempts forbidden write

```sql
begin;
select plan(2);
create extension if not exists "basejump-supabase_test_helpers";

-- Setup: one team, one human owner, one agent member
select tests.authenticate_as_service_role();
insert into teams (id, name) values ('11111111-1111-1111-1111-111111111111', 'Optimal');

select tests.create_supabase_user('alice', 'alice@optimal.ai');
select tests.create_supabase_user('agent_bot', 'bot@optimal.ai');

-- Tag the agent's app_metadata.role
update auth.users set raw_app_meta_data = '{"role":"agent"}'::jsonb
  where email = 'bot@optimal.ai';

insert into memberships (user_id, team_id, role) values
  (tests.get_supabase_uid('alice'),     '11111111-1111-1111-1111-111111111111', 'owner'),
  (tests.get_supabase_uid('agent_bot'), '11111111-1111-1111-1111-111111111111', 'agent');

-- POSITIVE: agent CAN propose into pending_reviews
select tests.authenticate_as('agent_bot');
select lives_ok(
  $$ insert into pending_reviews (team_id, title, status, proposed_by, target_table)
     values ('11111111-1111-1111-1111-111111111111', 'add SOP', 'open',
             auth.uid(), 'resources') $$,
  'agent may insert pending_reviews'
);

-- NEGATIVE: agent CANNOT insert directly into resources
select throws_ok(
  $$ insert into resources (team_id, name, type)
     values ('11111111-1111-1111-1111-111111111111', 'forbidden', 'reference') $$,
  '42501',
  'new row violates row-level security policy for table "resources"',
  'agent direct write to resources is rejected by RLS'
);

select * from finish();
rollback;
```

For UPDATE/DELETE (silent-filter case):
```sql
select is_empty(
  $$ update resources set name='hacked'
     where team_id = '11111111-1111-1111-1111-111111111111'
     returning id $$,
  'agent update of resources affects zero rows'
);
```

### Q3 — SessionStart hook running the sync script

`~/.claude/settings.json`:
```json
{
  "hooks": {
    "SessionStart": [
      { "matcher": "startup",
        "hooks": [
          { "type": "command",
            "command": "/Users/carterking/Projects/locker/variant-01/scripts/sync-skills.sh",
            "statusMessage": "Syncing Optimal skills" }
        ]
      }
    ]
  }
}
```

`scripts/sync-skills.sh`:
```bash
#!/bin/bash
set -euo pipefail
LOG=/tmp/cos-sync-$(date +%Y%m%d).log

# Detach heavy work; return fast so session start isn't blocked
( /usr/bin/env python3 "$CLAUDE_PROJECT_DIR/scripts/sync-skills.py" >>"$LOG" 2>&1 ) &
disown

# Structured context back to Claude
cat <<EOF
{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"COS skill sync started in background; tail $LOG"}}
EOF
exit 0
```

---

## Sources

- [JSON Web Token (JWT) | Supabase Docs](https://supabase.com/docs/guides/auth/jwts)
- [Custom Access Token Hook | Supabase Docs](https://supabase.com/docs/guides/auth/auth-hooks/custom-access-token-hook)
- [Custom Claims & RBAC | Supabase Docs](https://supabase.com/docs/guides/database/postgres/custom-claims-and-role-based-access-control-rbac)
- [User sessions | Supabase Docs](https://supabase.com/docs/guides/auth/sessions)
- [JWT Signing Keys | Supabase Docs](https://supabase.com/docs/guides/auth/signing-keys)
- [Python: signInWithPassword | Supabase Docs](https://supabase.com/docs/reference/python/auth-signinwithpassword)
- [Python: setSession | Supabase Docs](https://supabase.com/docs/reference/python/auth-setsession)
- [Advanced pgTAP Testing | Supabase Docs](https://supabase.com/docs/guides/local-development/testing/pgtap-extended)
- [pgTAP: Unit Testing | Supabase Docs](https://supabase.com/docs/guides/database/extensions/pgtap)
- [Testing on Supabase with pgTAP | Basejump](https://usebasejump.com/blog/testing-on-supabase-with-pgtap)
- [supabase-test-helpers | GitHub (Basejump)](https://github.com/usebasejump/supabase-test-helpers)
- [Testing RLS with pgTAP | Blair Jordan, Medium](https://blair-devmode.medium.com/testing-row-level-security-rls-policies-in-postgresql-with-pgtap-a-supabase-example-b435c1852602)
- [RLS test helper gist | mansueli](https://gist.github.com/mansueli/ede3563e5dec3e3d4beb88dcaaf66879)
- [Hooks reference | Claude Code Docs](https://code.claude.com/docs/en/hooks)
- [Session Lifecycle Hooks | claudefa.st](https://claudefa.st/blog/tools/hooks/session-lifecycle-hooks)

## Gaps / Uncertainty

- **Python supabase-py token-to-disk persistence** has no first-party doc; the `set_session(access, refresh)` + `refresh_session()` pattern above is inferred from API reference and JS client semantics. Verify in Stage 1.
- **SessionStart firing on `claude -c` resume from a different cwd** is not explicitly documented. Verify empirically in Stage 3.
- **Refresh-token reuse-window default of 10 seconds** is documented but the *parent token logic* edge cases (clock skew, network jitter) are best treated as opaque — don't build retry logic that assumes specific window math.
- **Custom Access Token Hook latency cost** isn't quantified in docs. If used on every sign-in for the agent it should be benchmarked before relying on it.
