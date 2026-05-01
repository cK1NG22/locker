# Decisions — Locker variant-01

Locked design decisions for this variant. **Append-only** — most recent first. Supersede with a new entry; do not edit historical ones.

For load-bearing architectural decisions, write a full ADR at `../../docs/decisions/0NNN-title.md` and reference it here.

## ADRs (in `../../docs/decisions/`)

ADR-0001..0003 as of 2026-04-27 (renumbered from mock-cos 0008/0009/0010 on 2026-04-29 when this work moved here).

- **ADR-0001** *(formerly mock-cos ADR-0008)* — Pure Supabase substrate; agent-as-principal via Supabase Auth's paved path; Optimal AI dogfood data — NOT Pinecrest.
- **ADR-0002** *(formerly mock-cos ADR-0009)* — Skills registry IN scope from Stage 1; sync-on-disk for Claude Code via `SessionStart` hook; coexist with Locker; MCP-fronted + Cursor adapter deferred.
- **ADR-0003** *(formerly mock-cos ADR-0010)* — Supabase schema parity: flatten Connectors into `resources.type='connector'`, drop UNIQUE_ID prefixes for UUIDs, Owner as Person FK to `auth.users`, mirror the Tasks DB gap as stage-N TODO.

## Open decisions

- **Future ADR (deferred):** Does variant-01 become Optimal AI's production COS substrate (replacing Adam's Notion), or stay a comparison artifact alongside?
- **Future ADR (deferred):** Locker variant-00 ↔ variant-01 consolidation — when does operational pain of running two backends exceed the differentiation value? (Per ADR-0002, no migration today.)
