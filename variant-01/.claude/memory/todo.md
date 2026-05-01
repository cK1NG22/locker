# TODO — Locker variant-01

Outstanding work, ordered by stage. Mutable — edit freely.

## Active

- [ ] **Carter unblock Stage 1** — create Supabase project at supabase.com/dashboard with name `optimal-cos`, generate + 1Password the DB password as `optimal-cos-db-password`, copy Project URL + anon key + service_role key into `scripts/.env`. Full Stage 0 checklist in `../../scripts/README.md` (steps 0.1–0.6).
- [ ] **Stage 1 → run + verify** once unblocked: `cd scripts && python3 stage_1_seed.py && python3 stage_1_verify.py`. Gate: 5/5 RLS tests GREEN before Stage 2 starts.
- [ ] **Stage 2** — `resources` table with `type='connector'` flatten (per ADR-0003) + RLS policies (read via membership, write blocked for agents via `not is_agent()`) + one seed row (Optimal AI's Company Info) + verify agent can read but not write.
- [ ] **Stage 3** — `skills` table + sync-on-disk script + `SessionStart` hook integration (per ADR-0002). First end-to-end skill sync. Pre-migration inventory at `../../docs/reference/skills-inventory.md` flagged the `locker` skill as the candidate first-skill-to-sync.
- [ ] **Stage 5 (deferred)** — real Optimal AI data migration. Re-fetch Adam's live Notion vocabularies (Resources DB, Skills DB, Projects DB) via Notion MCP before locking enum check constraints (per ADR-0003).
- [ ] **Stage-N TODO** — Add `tasks` table + Projects→Tasks relation + `completion_pct` rollup view to close the Tasks gap from mock-cos ADR-0007 Gate 8 / this variant's ADR-0003. Build when comparison test scenarios prove the rollup matters or Optimal AI project tracking needs hit the wall.

## Backlog

- [ ] Build a Cursor rules adapter that syncs `kind='prompt-only'` skills to `.cursor/rules/<slug>.mdc` (deferred per ADR-0002 with explicit trigger condition: Carter actively uses Cursor enough that filesystem-only sync feels limiting).
- [ ] Build an MCP-fronted server alongside sync-on-disk for cross-client reach (ChatGPT / Gemini) — deferred per ADR-0002.
- [ ] Filesystem → Supabase reverse sync — deferred per ADR-0002.
- [ ] Future ADR: whether the Supabase variant becomes Optimal AI's *production* COS substrate (replacing Adam's Notion) once dogfood proves out, or stays a comparison artifact alongside.

## Done

- [x] **2026-04-27** — ADR-0001 (formerly 0008) approved: pure Supabase, agent-as-principal, Optimal AI dogfood data.
- [x] **2026-04-27** — ADR-0002 (formerly 0009) approved: skills registry IN scope from Stage 1, sync-on-disk for Claude Code, coexist with Locker.
- [x] **2026-04-27** — ADR-0003 (formerly 0010) approved: schema parity — flatten Connectors, drop UNIQUE_ID prefixes for UUIDs, Owner as Person FK, mirror Tasks gap.
- [x] **2026-04-27** — Stage 1 prep landed: `scripts/0001_schema.sql` (teams + memberships + RLS + SECURITY DEFINER helpers), `scripts/stage_1_seed.py`, `scripts/stage_1_verify.py` (5 RLS tests including negative cases), `scripts/README.md` (full dashboard checklist), `scripts/.env.example`.
- [x] **2026-04-29** — Migrated from `~/Projects/mock-cos/` to `~/Projects/locker/variant-01/`. All Supabase work moved (scripts, prompts, docs/reference, ADRs renumbered). Cross-references updated.
