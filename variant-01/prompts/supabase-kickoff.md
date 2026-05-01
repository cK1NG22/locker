# Supabase COS — Session Kickoff Prompt

> **Historical document.** This prompt was used to kick off the planning session that produced ADRs `../docs/decisions/0001`, `0002`, `0003` (numbered 0008/0009/0010 at the time, in mock-cos). The three pre-build gates below are RESOLVED. To resume the in-flight build, see `../scripts/README.md` for current Stage 1 status (BLOCKED on Carter creating the Supabase project in the dashboard).
>
> Updated 2026-04-29: project moved from `~/Projects/mock-cos/` to `~/Projects/locker/variant-01/` (Supabase work is a Locker variant, not a Mock COS sandbox).

---

Paste this into a fresh Claude Code session in `~/Projects/locker/variant-01/`.

---

You're starting a session to **plan and build the Supabase variant — Locker's variant-01 substrate**. This is the first construction leg of the 4-way COS comparison: Adam's production Notion COS / Mock COS Notion (Pinecrest sandbox) / **Supabase variant (this build, Optimal AI dogfood)** / GitHub variant (later).

## Load-bearing context (read before doing anything)

Memory files (auto-loaded via the memory system — open them):
- `hub-locker.md` — Locker hub; this work is variant-01
- `hub-mock-cos.md` — Mock COS hub (Notion side); for the Pinecrest sandbox + Adam's spec — this variant references but does not extend it
- `research-supabase-vs-notion-cos.md` — substrate comparison, RBAC depth, hybrid option, the principal-model takeaway
- `project-supabase-cos-skills-backend.md` — strategic angle: same Supabase backend can double as a Claude skills registry (sync-on-disk OR MCP-fronted, like Locker)
- `feedback-incremental-build-not-scaffold-first.md` — build one piece deeply, never scaffold-all-then-fill
- `feedback-simplify-first.md` — start with the simplest thing that works
- `feedback-plain-naming-no-jargon.md` — short plain words in table/file/repo names
- `feedback-open-prompts-beat-menus.md` — for scope decisions, use open text not multiple choice

Project files:
- `~/Projects/locker/CLAUDE.md` — variant chooser at repo root
- `~/Projects/locker/variant-01/CLAUDE.md` — variant-01 scope + hard rules
- `~/Projects/locker/variant-01/docs/decisions/` — ADRs 0001 (substrate + principals), 0002 (skills registry), 0003 (schema parity)
- `~/Projects/mock-cos/docs/reference/v14-spec-snapshot-2026-04-23.md` — frozen v1.4 schema (lives in mock-cos because it applies to both Notion and Supabase variants; also check the live Notion spec before structural calls)
- `~/Projects/mock-cos/OPEN_QUESTIONS.md` — Mock COS open design questions (Q3 + Q5 have Supabase-scoped resolutions in this variant's ADR-0003)

## Pre-build gates (resolve in plan, capture as ADRs)

1. **Pure Supabase vs hybrid** (Notion frontend + Supabase backend + sync layer). Frame the principal-model question explicitly: who's the actor on each request — user / agent / agent-on-behalf-of-user?
2. **Skills registry — in-scope or out-of-scope?** If in: pick architecture (sync-on-disk OR MCP-fronted). If out: Locker stays the skill-distribution layer; Supabase stays focused on COS data.
3. **Schema parity strategy** — what stays 1:1 with v1.4, what gets re-shaped for relational reality (Connectors hybrid pattern, the Tasks DB gap flagged in Gate 8, Skills/Resources vocab divergences).

## Session deliverables

1. **Enter `/plan` mode first.** Plan must cover: substrate decision (pure/hybrid), schema sketch (DDL or near-DDL), RLS + auth model, agent JWT approach, sync-with-Notion design (if hybrid), and the comparison test scenarios this build needs to support.
2. **After plan approval → ADRs:** *(RESOLVED 2026-04-27)*
   - ADR-0001: Pure vs hybrid (with principal-model framing) → pure Supabase, agent-as-principal, Optimal AI dogfood
   - ADR-0002: Skills registry scope (and architecture if in-scope) → IN scope from Stage 1, sync-on-disk for Claude Code, coexist with Locker
   - ADR-0003: Schema parity decisions → flatten Connectors, drop UNIQUE_ID prefixes for UUIDs, Owner as Person FK, mirror Tasks gap
3. **After ADRs → build incrementally.** One table + its RLS + one read/write path, verified end-to-end, *then* iterate. Do not scaffold all tables first.

## Hard rules

- Never use `service_role` from agents — always scoped JWTs (RBAC footgun #1; see research file)
- Stop at gates; don't barrel through unresolved decisions
- Don't auto-create the Supabase project — ask Carter first (he may want to use an existing project or create it in the dashboard himself)
- Carter is non-technical — explain SQL / auth / RLS concepts inline as you go
- This was previously a thinking-only project (per `CLAUDE.md`) — adding code may warrant updating the project rules; flag before doing so

## First move

Load the memory files above, scan the v1.4 schema snapshot, then open `/plan` mode and walk Carter through the three pre-build gates one at a time using open prompts.
