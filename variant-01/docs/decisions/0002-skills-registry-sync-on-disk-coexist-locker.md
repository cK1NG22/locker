# ADR-0002: Skills registry — IN scope, sync-on-disk for Claude Code, coexists with Locker

**Date:** 2026-04-27 (renumbered from mock-cos ADR-0009 on 2026-04-29 when this work moved to Locker variant-01)
**Status:** Accepted
**Supersedes:** `~/Projects/mock-cos/docs/decisions/0009-skills-registry-sync-on-disk-coexist-locker.md` (file removed in the same restructure)
**Decision drivers:** Plan approved 2026-04-27 (`~/.claude/plans/dreamy-syncing-supabase.md`). Resolves Gate 2 of three pre-build gates. Strategic angle articulated in `project-supabase-cos-skills-backend.md` (global memory).

## Context

ADR-0001 establishes Supabase as Optimal AI's COS substrate dogfood. A separate strategic question — captured in `project-supabase-cos-skills-backend.md` — sits alongside: **the same Supabase backend can double as a Claude skills registry consumed by Claude Desktop, Claude Code, and (via MCP) Cursor / ChatGPT / Gemini.** One backend, two consumers, shared RLS / auth / team-scoping infrastructure.

Two viable architectures exist:

- **Sync-on-disk** — Supabase is source of truth. A small script (cron or `SessionStart` hook in `~/.claude/settings.json`) reads Supabase and writes `~/.claude/skills/<slug>/SKILL.md` files. Claude Code autoloads at session start via `description:`-driven natural-language triggers. Skills behave as first-class citizens (`/<slug>` invocation, autoload on matching phrases). Edits not live until next sync. Filesystem reach is naturally Claude-Code-shaped.

- **MCP-fronted (Locker shape)** — Supabase content sits behind an MCP server. Skills become tools clients call by name (one tool per skill, or generic `run_skill(name, args)`). Live updates, central revocation, audit log. Cross-client reach (Cursor / ChatGPT / Gemini all speak some form of MCP). Skills do *not* autoload from natural language; clients must know to invoke the tool.

The Locker MCP server already implements the MCP-fronted pattern for team-managed shareable skills — that's an existence proof of the pattern in production today.

The behavioral gap matters more than the names suggest. Sync-on-disk preserves Claude Code's description-driven natural-language autoload (the feature that makes skills feel like first-class extensions to the agent). MCP-fronted breaks that: skills become tools you have to invoke deliberately. Trade discoverability for live updates and cross-client reach.

Reach across the four major clients on Carter's Mac is uneven:
- **Claude Code** — `~/.claude/skills/<slug>/SKILL.md` is the paved path; sync-on-disk works natively.
- **Cursor** — `.cursor/rules/*.mdc` per-project (and `~/.cursor/` user-level) accept a similar-but-different format. **Rules ≠ skills:** Cursor rules can't host tools/scripts, only prompt context. Pure-prompt skills translate; tool-bearing skills don't translate at all.
- **ChatGPT (desktop/web)** — Custom GPTs and Projects live on OpenAI's servers, not the filesystem. No local-file path. MCP only.
- **Gemini** — Gems live on Google's servers; the CLI has no skill registry. MCP only.

## Decision

**Skills are IN scope from stage 1** of the Supabase build. The schema includes a `skills` table from the start, alongside the COS tables, populated via real migration of existing `~/.claude/skills/` content in Stage 5.

**Architecture: sync-on-disk for Claude Code as the stage-1 delivery mechanism.**
- Direction: Supabase → filesystem, one-way. Filesystem → Supabase reverse sync deferred to a v2 of the sync script.
- Trigger: `SessionStart` hook in `~/.claude/settings.json` calls the sync script on every Claude Code session start. Cron is a fallback for unattended runs.
- Sync target: `~/.claude/skills/<slug>/SKILL.md` plus any referenced files from the `files` JSONB column on the `skills` row.
- Delivery script lives at `scripts/sync-skills.py` (or equivalent) inside `~/Projects/locker/variant-01/`.

**Coexists with Locker, no migration.** Locker keeps its current scope (team-managed shareable skills via the Locker MCP server). The Supabase variant handles Optimal-internal + personal skills via filesystem sync. Two systems, two roles, clean differentiation:
- **Locker (MCP-fronted, unchanged):** "things multiple people use" layer. Team-managed shareable skills. Multi-client reach (where supported). Live updates. Central revocation. Audit log.
- **Supabase variant (sync-on-disk):** "your own working set" layer. Optimal-internal + personal skills. Description-driven natural-language autoload. Skill-as-first-class-citizen UX. Works offline.

If the Supabase variant were *also* MCP-fronted, the two systems would compete for the same surface area — every skill addition would force a "is this Locker or Supabase?" decision. Splitting on shape (sync-on-disk for personal, MCP-fronted for team-shared) lets each system do what only it can do well.

**Schema implication: `kind` column on `skills`.** Values: `prompt-only` | `tool-bearing`. Distinguishes skills that *could* round-trip to Cursor's rules format (prompt-only) from those that are Claude-Code-only (tool-bearing). Future Cursor adapters key off this column.

**Deferred extensions, with explicit trigger conditions:**

| Extension | Trigger condition |
|---|---|
| **Cursor rules adapter** (sync `kind='prompt-only'` skills to `.cursor/rules/<slug>.mdc`) | Carter actively uses Cursor enough that filesystem-only sync (Claude Code) feels limiting |
| **MCP-fronted server** (Supabase-backed MCP server alongside sync-on-disk, for cross-client reach) | ChatGPT or Gemini reach becomes useful — e.g., colleague joins who uses ChatGPT, or value emerges in non-Claude-Code agents accessing Optimal's skills |
| **Filesystem → Supabase reverse sync** | Authoring SKILL.md files locally and pushing to DB becomes more frequent than DB-as-source-of-truth editing |
| **Locker → Supabase migration** (consolidate onto one backend) | Operational pain of running two backends exceeds the differentiation value |

Each extension is an additive build, not a replacement. MCP-fronted, when/if added, sits *alongside* sync-on-disk, not in place of it.

## Consequences

**Enables.**
- One backend for both COS data and skills registry — shared RLS / auth / team-scoping. Per-team (Optimal AI) skill scoping inherits from the same `team_id`-based RLS as Resources.
- Description-driven natural-language autoload preserved. The Claude Code "skills feel first-class" UX survives the migration.
- Skill changes are auditable via Postgres (`created_by`, `updated_at`, optional `pending_reviews` flow), unlike the current opaque-edits-on-filesystem model.
- RLS-scoped personal skills become possible — "Carter's personal skills sync only to Carter's laptop, not Adam's" — which `~/.claude/skills/` cannot do natively. This is meaningful for actual multi-person Optimal AI usage.

**Gives up.**
- Cross-client reach (Cursor / ChatGPT / Gemini) deferred. Stage 1 delivery is Claude-Code-only. Cursor partial via future adapter.
- Live edits across machines: edit a skill in the DB, it doesn't appear on a second machine until that machine syncs. Acceptable for personal/Optimal-internal skills (low edit frequency); would not be acceptable for team-shared skills, which is exactly why Locker stays MCP-fronted.
- Cursor adapter (when built) is lossy: tool-bearing skills won't appear there.

**Watchpoints.**
- Sync-on-disk requires byte-stable round-tripping — a SKILL.md written from a `skills` row, then re-read, must match. Schema design for `skills.body`, `skills.files`, and frontmatter generation needs to preserve trailing newlines, ordering of frontmatter keys, and any whitespace conventions Claude Code's parser depends on. Flag for Stage 3 acceptance test.
- `SessionStart` hook failure modes: if the sync script throws, does the Claude Code session start without skills, or fail outright? Acceptable behavior must be defined before Stage 3 ships. (Subagent research in flight is gathering this.)
- Skill-trigger collisions between Locker-served skills and Supabase-synced skills: both populate Claude Code's skill catalog. Naming conflicts → unpredictable autoload. Stage 5 migration must check for slug collisions with currently-installed Locker skills.

**Downstream.**
- Stage 3 of the build implements `skills` table + sync script + first end-to-end skill sync.
- Stage 5 (real data migration) imports existing `~/.claude/skills/` content into Supabase. Pre-migration inventory categorizing existing skills by `kind` and `scope` is in flight (subagent task) and will be consulted before Stage 5 starts.
- A future ADR addresses Locker → Supabase migration if/when consolidation onto one backend becomes valuable. Not in scope today.

## Related

- `~/.claude/plans/dreamy-syncing-supabase.md` (approved plan)
- `~/.claude/projects/-Users-carterking/memory/project-supabase-cos-skills-backend.md` (the strategic insight that prompted this ADR)
- `~/.claude/projects/-Users-carterking/memory/feedback-incremental-build-not-scaffold-first.md` (governs the staged delivery and the deferred-extensions pattern)
- `~/.claude/projects/-Users-carterking/memory/feedback-simplify-first.md` (chose sync-on-disk over the more ambitious "Both" architecture for stage 1)
- ADR-0001 (substrate + principal model — this ADR builds on its agent-JWT decision)
- ADR-0003 (schema parity — `skills` table sits alongside the COS schema there, with the `kind` column defined)
