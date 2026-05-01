# Progress Log — Locker variant-01

Session-by-session log. **Append-only** — most recent first.

Format: `## YYYY-MM-DD — Short summary` followed by 1-3 sentences on what changed.

---

## 2026-05-01 — Migrated from mock-cos to Locker variant-01

Cross-project restructure: Supabase work moved out of `~/Projects/mock-cos/` (Notion COS sandbox) into `~/Projects/locker/variant-01/` (storage-layer dogfood). 12 files copied (5 scripts + 1 prompt + 3 reference docs + 3 ADRs). ADRs renumbered: mock-cos 0008/0009/0010 → variant-01 0001/0002/0003 with `**Supersedes:**` headers preserving the audit trail. Cross-references rewired throughout (ADR↔ADR, kickoff prompt, scripts/README, reference docs). variant-01 CLAUDE.md written carrying over the Supabase hard rules. This `.claude/memory/` tree scaffolded with cherry-picked Supabase entries — Notion-COS entries stayed in mock-cos. Locker repo restructured into variant-00 (existing FastAPI MCP build) + variant-01 (this Supabase variant) under one git repo. Pre-restructure state preserved at git tag `pre-variant-restructure` (commit f3a302c). Stage 1 still BLOCKED on Carter creating the Supabase project in the dashboard.

## 2026-04-29 (Session 2) — Supabase Stage 0.1 walkthrough

Walked through Stage 0.1 with Carter: create Supabase project at supabase.com/dashboard with name `optimal-cos`, generate + 1Password the DB password as `optimal-cos-db-password`, copy Project URL + anon key + service_role key into a scratch note for the upcoming `.env`. Stage 1 still BLOCKED on Carter doing 0.1–0.6 per `scripts/README.md`.

## 2026-04-28 — Handoff prepared at end of Supabase build kickoff session

Stage 1 BLOCKED on Carter doing Supabase dashboard work (full checklist in `scripts/README.md` Stage 0.1–0.6); Stage 2 (resources + RLS) is the next action once `stage_1_verify.py` shows 5/5 GREEN.

## 2026-04-27 (later) — Supabase build planning + Stage 1 prep complete

Three pre-build gates resolved interactively → ADR-0001 *(then 0008)* (pure Supabase, agent-as-principal via Supabase Auth's paved path, Optimal AI dogfood data — NOT Pinecrest), ADR-0002 *(then 0009)* (skills registry IN scope from stage 1, sync-on-disk for Claude Code via `SessionStart` hook, coexist with Locker, MCP-fronted + Cursor adapter deferred with explicit trigger conditions), ADR-0003 *(then 0010)* (schema parity: flatten Connectors into `resources.type='connector'` single-table model, drop UNIQUE_ID prefixes for UUIDs, Owner becomes Person FK to `auth.users`, mirror the Tasks DB gap as stage-N TODO). Plan approved: `~/.claude/plans/dreamy-syncing-supabase.md`. Three background subagents returned reference artifacts: `docs/reference/supabase-build-research.md` (agent-JWT patterns + RLS testing gotchas + SessionStart hook semantics), `docs/reference/skills-inventory.md` (65 skills classified, `locker` flagged as Stage 3 first-skill-to-sync candidate), `docs/reference/existing-supabase-patterns.md` (no existing Supabase code in any repo — clean slate, reference Locker's *shape* not its *stack*). Stage 1 prep landed: `scripts/0001_schema.sql` (teams + memberships + RLS + SECURITY DEFINER helpers `is_team_member`/`is_team_owner`/`is_agent`), `scripts/stage_1_seed.py`, `scripts/stage_1_verify.py` (5 RLS tests including negative cases per `throws_ok()` for INSERT and `is_empty()` for UPDATE/DELETE), `scripts/README.md` (full dashboard checklist), `.gitignore` at repo root, `scripts/.env.example`. **Stage 1 BLOCKED on Carter creating Supabase project + filling `.env` + running 0.4-0.6 in dashboard.**

## 2026-04-27 — Captured Supabase + GitHub COS variant TODOs

Verdict: not new projects yet — when construction starts, rename hub → `hub-cos-comparisons.md` (plain naming, not "substrate"). *(2026-04-29 update: this naming idea was superseded — Supabase work became Locker variant-01 instead of a new hub.)* Created paste-ready kickoff prompt at `prompts/supabase-kickoff.md` for the next planning+build session.
