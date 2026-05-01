# Locker variant-01 — Supabase Substrate

Migrated from `~/Projects/mock-cos/scripts/` + Supabase ADRs on 2026-04-29. **Optimal AI's actual team data** modeled in Postgres; agent-as-principal via Supabase Auth's paved path.

This variant exists to dogfood the Locker pitch primitive: *"your agent only sees what your firm has granted it"* — a Postgres RLS sentence that Notion can't express. Comparison axis: Adam's production Notion (Optimal AI data) / Mock COS Notion (Pinecrest, separate friction-test) / **this variant (Optimal AI data)** / future GitHub variant.

## Scope

- **Optimal AI's real team data**, not Pinecrest.
- Pure Supabase (no Notion frontend, no sync layer to Notion).
- Agent-JWT principals, not service-role-from-agent.
- Skills registry IN scope from Stage 1, sync-on-disk for Claude Code (per ADR-0002).

## Hard rules

1. **Never use `service_role` from agents.** Agents always use scoped JWTs from `signInWithPassword`. Service-role belongs only to admin scripts running locally as Carter.
2. **Env-var discipline.** `.env`, `~/.config/optimal-cos/agent.token`, and any DDL containing real org/people names are gitignored. Never committed.
3. **Never paste production schemas, connection strings, service-role keys, or real client data into shared docs/Slack/PRs.**
4. **Incremental build.** Per `~/.claude/projects/-Users-carterking/memory/feedback-incremental-build-not-scaffold-first.md`. Stage 1 → Stage 5 sequentially. No scaffolding ahead of the current stage.
5. **Stage 1 is BLOCKED on Carter creating the Supabase project in the dashboard.** Don't unblock or run Stage 1 from any restructure work — only Carter's manual dashboard step unblocks it.

## Repo map

- `scripts/` — Stage 1 SQL migration + seed/verify Python + dashboard checklist (see `scripts/README.md`)
- `prompts/supabase-kickoff.md` — paste-ready kickoff prompt for the next planning+build session
- `docs/decisions/` — ADRs 0001 (substrate + principals), 0002 (skills registry sync-on-disk), 0003 (schema parity)
- `docs/reference/` — supabase-build-research, existing-supabase-patterns, skills-inventory (referenced by ADR-0002 Stage 5 work)
- `.claude/memory/` — variant-01 project memory (cherry-picked Supabase entries from mock-cos's memory on 2026-04-29)

## Plan

`~/.claude/plans/dreamy-syncing-supabase.md` — approved 2026-04-27. Stage 1 prep complete. **Stage 1 BLOCKED on Carter dashboard work** (full checklist in `scripts/README.md` Stage 0.1–0.6).

## Hub

Project hub: `~/.claude/projects/-Users-carterking/memory/hub-locker.md` (renamed from `hub-locker-v2.md` on 2026-04-29).
