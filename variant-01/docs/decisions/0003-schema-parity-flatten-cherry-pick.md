# ADR-0003: Schema parity — flatten Connectors, mirror Tasks gap, cherry-pick vocab to Adam's live production

**Date:** 2026-04-27 (renumbered from mock-cos ADR-0010 on 2026-04-29 when this work moved to Locker variant-01)
**Status:** Accepted
**Supersedes:** `~/Projects/mock-cos/docs/decisions/0010-schema-parity-flatten-cherry-pick.md` (file removed in the same restructure)
**Decision drivers:** Plan approved 2026-04-27 (`~/.claude/plans/dreamy-syncing-supabase.md`). Resolves Gate 3 of three pre-build gates. Inputs: v1.4 spec snapshot at `~/Projects/mock-cos/docs/reference/v14-spec-snapshot-2026-04-23.md` (lives in mock-cos because the spec applies to both Notion and Supabase variants; live: https://www.notion.so/344b5735d29381a482aace7e8d054737), Mock divergences flagged in mock-cos ADR-0007 Execution Findings, mock-cos OPEN_QUESTIONS Q3.

## Context

The v1.4 COS Directory Spec was designed against Notion's quirks. Some of its structural choices express real semantics; others are Notion-UI workarounds that exist only because Notion couldn't satisfy two requirements at once. Re-implementing v1.4 in Postgres (per ADR-0001) requires a schema-parity philosophy: where do you mirror v1.4 verbatim (so the Supabase variant remains comparable to Adam's Notion COS), and where do you let Postgres be Postgres (so the variant is good Postgres, not a port of a Notion port)?

Three sub-questions sat tangled inside Gate 3:

**3a. The Connectors hybrid pattern.** v1.4 nests a Connectors DB inside a directory row in Resources, with both a gallery view and a table view. The schema columns of the nested DB (`Name, Summary, Status, Function, Owner, Last Verified, Tags`) are *exactly* a subset of Resources' columns — there are zero connector-specific schema fields. The nesting + dual-view pattern exists purely because Notion couldn't simultaneously offer "one connector per row," "visual gallery navigation," and "auditable typed properties" without it. The contortion is a Notion UI artifact, not a semantic distinction.

**3b. The Tasks DB gap.** Adam's production Projects has a Tasks relation + Completion rollup. Mock COS Notion + Optimal AI COS Template (per ADR-0007) do not — flagged as the highest-severity divergence in ADR-0007 Gate 8 Execution Findings. Postgres makes this trivial to close (a `tasks` table + `count(*) filter (...) / count(*)` view), so "skip it because it's hard" doesn't apply.

**3c. Vocabulary divergences.** Mock has 8+ enum-level divergences from Adam's production: Resources Type (`Process-SOP` hyphen vs `Process/SOP` slash, OPEN_QUESTIONS Q3), Skills Category (5 values vs 7), Skills Status (`select` vs Notion's `status` type), Owner (text vs person), Resources Function (5 values vs 8), Resources Tags (different vocabularies entirely), nested Connectors `Type` property. The CLAUDE.md project rule says: *"When the spec and the live pages disagree, mirror the live pages and flag the divergence as an ADR watchpoint."* For the Supabase variant, "live pages" = Adam's production Notion COS, since this is dogfood (per ADR-0001).

A meta-decision sits behind all three: **what is schema parity actually for in this build?** If it's "make the Supabase variant interchangeable with Adam's Notion COS for comparison," strictness wins (port even the contortions). If it's "let Postgres be Postgres and make the comparison reveal what each substrate naturally produces," looseness wins (embrace divergences). If it's "this is the dogfood substrate Optimal AI might actually use," cherry-picked correctness wins (fix what's broken, mirror what works).

## Decision

The build is dogfood (per ADR-0001), and schema parity exists to **expose substrate-natural design** while preserving v1.4's load-bearing semantics. Cherry-pick across the three sub-questions:

### 3a — Flatten Connectors into `resources.type = 'connector'`

Single `resources` table. No separate `connectors` table. No nested directory-row wrapper. Connectors are rows where `type = 'connector'`. The query `select * from resources where type = 'connector'` *is* the connectors view. Same `team_id`, RLS policies, Owner FK, Tags, Last Verified — connectors share Resources' schema natively because v1.4's nested Connectors DB schema *was already a subset of Resources' schema*.

Agent-cost perspective: navigating connectors is one indexed query (`(team_id, type)` index) vs. one wrapper-row fetch + one nested-collection traversal in Notion. The Notion contortion is purely human-UI, with no agent benefit; Postgres unwinds it for free.

### 3b — Mirror the Tasks gap in stage 1

No `tasks` table at launch. Captured as a stage-N TODO in this variant's `.claude/memory/todo.md` (and reflected in the global `hub-locker.md` Locker hub). The gap closes later when (a) comparison test scenarios prove the rollup matters, or (b) Optimal AI's actual project-tracking needs hit the wall the gap creates, whichever comes first.

This is a deliberately conservative choice — Postgres makes the table trivial to add, but per `~/.claude/projects/-Users-carterking/memory/feedback-incremental-build-not-scaffold-first.md`, every non-essential table at stage 1 is a stub that rots. Mirror the gap, capture the TODO, close it when the need is real.

### 3c — Cherry-pick vocabulary against Adam's *live* production

Specifics:

- **UNIQUE_ID prefixes dropped entirely.** UUIDs are the primary keys (`id uuid primary key default gen_random_uuid()`). An optional `display_id text` column is reserved on `resources`, `skills`, `projects` and defaults to `NULL`. Carter to decide later whether to populate it (e.g., human-readable IDs in URLs). The `MSKL`/`SKL`/`PRJ`/`TSKL`/`TPRJ` family of prefixes existed only because Notion enforces unique prefixes per workspace — Postgres has no such constraint, so the workaround vanishes. Resolves mock-cos OPEN_QUESTIONS Q5 by sidestepping the question.
- **`Owner` becomes a Person FK** (`owner_id uuid references auth.users(id)`), not text. Closes the Mock/Template HIGH-severity gap from mock-cos ADR-0007 Gate 8 by accident — a foreign key is just the right Postgres model. Placeholder rendering (`[Partner Name]` in the Template) becomes a UI concern, not a schema concern. UI/seed data substitutes the unassigned-owner case with `NULL`.
- **Resources `Type` enum** matches Adam's vocabulary verbatim. SQL representation: `check (type in ('company_info','process_sop','connector','reference','template','external_reference'))`. Mock's `Process-SOP` (hyphen, mock-cos OPEN_QUESTIONS Q3) yields to Adam's `Process/SOP` (slash); both serialize to `process_sop` in the SQL enum.
- **Skills `Category`, Resources `Function`, Status fields, Tags vocabularies:** schema treats these as plain `text` (or `text[]` for tags) at stage 1. Vocabulary is locked at population time (Stage 5) by re-reading Adam's *then-current* live production via Notion MCP and applying check constraints. This defers vocabulary commitment until we have real data, which avoids re-migrations if Adam's spec evolves between now and Stage 5.
- **Status semantics:** Adam uses Notion's `status` type (Not started / In progress / Done) which is Kanban-style. Schema represents this as `text` for now; check constraints applied during Stage 5 if Adam's production has stabilized.

## Consequences

**Enables.**
- One unified `resources` table for agent queries — no UNION across resources/connectors, no JOIN through a wrapper row. Cheapest possible navigation surface.
- UUIDs sidestep workspace-scoped UNIQUE_ID constraints permanently. Future workspace-merge or cross-instance migration scenarios become trivial.
- `Owner` as FK enables relational queries: "all Resources owned by Adam," "all Projects without an Owner," correct deletion cascades, JOIN to user metadata. Notion's text-Owner model couldn't express any of these without LIKE matching.
- Deferred vocabulary commitment (text columns at stage 1, check constraints at Stage 5) means Adam's spec can evolve between now and real-data migration without forcing a schema migration on us.

**Gives up.**
- Direct human-readable refs in URLs/IDs (`SKL-12`) gone unless Carter opts to populate `display_id`. UUIDs everywhere.
- Mirror-the-gap (Tasks) means the Supabase variant has a known incomplete piece relative to Adam's production. Comparison test scenarios should account for this.
- Some v1.4 structural fidelity is lost — the Connectors directory-row wrapper does not exist in Postgres. A tester comparing "navigate to the Connectors page" between Notion and Supabase will find no equivalent landing surface in Supabase.

**Watchpoints.**
- v1.5+ of Adam's spec may unify Status types, change the Connector schema, or close the Tasks gap. Schema migration should re-check parity at that point. The CLAUDE.md "live pages, not snapshot" rule applies — re-fetch before each Stage gate that touches schema.
- If `display_id` columns end up unused for several stages, drop them in a future migration to keep schema tidy. They're cheap to keep but add noise.
- `Owner` FK to `auth.users` means deleting an `auth.users` row cascades to all owned Resources/Projects — not always desirable. Stage 1's RLS includes a `set null` cascade for owner deletes (so resources stay, owner clears) rather than `cascade` (so resources die with their owner).

**Downstream.**
- Stage 1 SQL files materialize this schema with `team_id`-scoped RLS.
- Stage 5 (real data migration) re-checks Adam's live production vocabularies before locking enum constraints — Notion-MCP fetch of Resources DB, Skills DB, Projects DB to capture current `Type` / `Function` / `Category` / `Status` / `Tags` values.
- A future ADR addresses Tasks DB shape if/when the gap closes. Schema design (FK direction, completion rollup, dependencies relation) is open until that ADR.

## Related

- `~/.claude/plans/dreamy-syncing-supabase.md` (Schema sketch section)
- `~/Projects/mock-cos/docs/reference/v14-spec-snapshot-2026-04-23.md` (frozen spec; live version at https://www.notion.so/344b5735d29381a482aace7e8d054737)
- ADR-0001 (substrate + principal — RLS protects this schema; Owner FK references the `auth.users` it establishes)
- ADR-0002 (skills registry — `skills` table sits alongside this schema, with `kind` column defined there)
- mock-cos ADR-0007 Execution Findings (Gate 8 schema-parity diff that surfaced these divergences; lives in `~/Projects/mock-cos/docs/decisions/`)
- mock-cos ADR-0004 (Connectors as nested DB per v1.4 — this ADR explicitly diverges in Postgres while preserving the v1.4 semantic; lives in `~/Projects/mock-cos/docs/decisions/`)
- mock-cos OPEN_QUESTIONS Q3 (`Process-SOP` vs `Process/SOP` — resolved by enum-canonicalization to `process_sop`)
- mock-cos OPEN_QUESTIONS Q5 (`MSKL`/`MPRJ` prefix divergence — sidestepped by dropping prefixes entirely in favor of UUIDs)
- mock-cos CLAUDE.md project rule: *"When the spec and the live pages disagree, mirror the live pages and flag the divergence as an ADR watchpoint."* (still applies to the Notion side; this variant inherits the principle for its dogfood-against-Adam's-live-Notion source-of-truth)
