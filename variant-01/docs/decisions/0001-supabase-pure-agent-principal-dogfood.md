# ADR-0001: Supabase variant is pure substrate, agent-as-principal, Optimal AI dogfood

**Date:** 2026-04-27 (renumbered from mock-cos ADR-0008 on 2026-04-29 when this work moved to Locker variant-01)
**Status:** Accepted
**Supersedes:** `~/Projects/mock-cos/docs/decisions/0008-supabase-pure-agent-principal-dogfood.md` (file removed in the same restructure)
**Decision drivers:** Plan approved 2026-04-27 (`~/.claude/plans/dreamy-syncing-supabase.md`). Resolves Gate 1 of three pre-build gates surfaced in `../../prompts/supabase-kickoff.md`. Substrate analysis in `research-supabase-vs-notion-cos.md` (global memory).

## Context

The Mock COS investigation produced a 4-way substrate comparison framing: Adam's production Notion COS / Mock COS Notion / Supabase variant / GitHub variant. Building the Supabase variant requires answering a question Notion lets you punt: **who is the actor on each request?** Notion's access model collapses to "whoever OAuth'd is the actor" — exactly one principal per request, always the human. Postgres + RLS forces an explicit answer up front, because every policy is written against `auth.jwt()`.

Three sub-questions sat tangled inside Gate 1:

**1a. Pure Supabase vs hybrid (Notion frontend + Supabase backend + sync layer).** The hybrid option matches Locker's design — Notion-style human surface, Postgres machine surface, sync between. It preserves Notion's "open the page, read your COS as a beautiful document" UX. But it pays for that with a sync layer that has to reconcile two principal models — Notion's "always the OAuth'd user" with Supabase's "agent / user / agent-on-behalf-of-user" distinctions. Sync layers fail in the direction of the weaker model: Notion → Supabase sync collapses agent identity into user identity, which forces service-account writes on the Supabase side, which is the RBAC footgun the substrate research file flags.

**1b. Principal model.** Three viable shapes: (i) agent borrows the user's JWT (simple, but no audit separation), (ii) agent has its own row in `auth.users` with its own JWT (most expressive, native to Locker's pitch), (iii) agent-on-behalf-of-user with delegated JWTs carrying both claims (most precise, most schema/policy work). The Locker pitch primitive — "your agent only sees what your firm has granted it" — requires (ii) at minimum.

**1c. Whose firm does this build model?** Mock COS Notion already models Pinecrest (8-person fictional consulting firm) as a friction-test sandbox. Modeling Pinecrest in Supabase too would give apples-to-apples substrate comparison but wouldn't dogfood RLS-scoped agents (Pinecrest team members are fictional; their JWTs would be synthetic). Modeling Optimal AI's actual team data dogfoods the Locker pitch on real principals at the cost of comparing different data shapes between Mock and Supabase.

## Decision

The Supabase variant is built as **(a) pure Supabase**, no Notion frontend, no sync layer; **(b) agent-as-its-own-principal** via Supabase Auth's paved path — each agent is a row in `auth.users` with `app_metadata.role = 'agent'`, JWTs minted via standard `signInWithPassword`, never `service_role` from agents; **(c) modeling Optimal AI's actual team data** (Locker dogfood), not Pinecrest.

This makes the Supabase variant a different artifact than "Mock COS in Supabase." It is a Supabase variant of *Adam's production COS structure*, populated with Optimal AI's internal data. The 4-way comparison axis becomes: Adam's production Notion (Optimal AI data) / Mock COS Notion (Pinecrest, separate friction-test question) / **Supabase variant (Optimal AI data, this build)** / GitHub variant (later).

## Consequences

**Enables.**
- 4-way comparison cleanly separates substrate axis (Adam's Notion + Supabase + future GitHub, all Optimal AI data) from data-fidelity axis (Mock Notion holds Pinecrest, answers a different question).
- First real dogfood of agent-as-distinct-principal — required for Locker's "your agent only sees what your firm has granted it" pitch primitive.
- Removes sync-layer coordination cost. The Supabase variant is its own artifact, evaluable on its own terms; no two-system reconciliation seam to debug.
- Native Postgres event-driven automation (triggers + realtime) unlocks the substrate difference flagged in `research-supabase-vs-notion-cos.md` Section 1 — Notion can't do this and the Mock variant won't show it.

**Gives up.**
- Mock COS Notion and Supabase variant are no longer directly comparable as "same data, different substrate." The Pinecrest sandbox remains valid for substrate-agnostic friction-test purposes; the substrate comparison happens on Optimal-AI-shaped data across three of four variants.
- No Notion frontend over Optimal AI's data on Supabase. Humans read SQL queries (or any frontend we build later); Notion's "click around, read the COS as a beautiful document" UX is forfeited for this variant. Whether that's a real loss depends on how often humans navigate the COS vs. agents — open question, surfaces in the comparison test scenarios.

**Bumps the data-handling bar.**
- This build holds **real Optimal AI internal data**, not mock data. No production schemas in shared docs/Slack/PRs. No committing connection strings or service-role keys. `~/.config/optimal-cos/agent.token`, `.env`, and any DDL containing real org/people names must be gitignored. Service-role key never touches disk in cleartext outside Carter's local `~/.config/`.

**Downstream.**
- ADR-0002 (skills registry scope) and ADR-0003 (schema parity strategy) are immediate dependents.
- `~/.claude/projects/-Users-carterking/memory/hub-mock-cos.md` Supabase TODO has been moved out — this work now lives in Locker variant-01, not as a TODO under mock-cos.
- A future ADR (TBD, deferred) will address whether the Supabase variant becomes Optimal AI's *production* COS substrate (replacing Adam's Notion) once dogfood proves out, or stays a comparison artifact alongside.

## Related

- `~/.claude/plans/dreamy-syncing-supabase.md` (approved 2026-04-27 — the plan this ADR ratifies)
- `../../prompts/supabase-kickoff.md` (kickoff prompt that defined the three pre-build gates)
- `~/.claude/projects/-Users-carterking/memory/research-supabase-vs-notion-cos.md` (substrate comparison, RBAC depth, hybrid option, principal-model takeaway)
- `~/.claude/projects/-Users-carterking/memory/project-supabase-cos-skills-backend.md` (the skills-registry strategic angle, addressed in ADR-0002)
- ADR-0002 (skills registry scope — sync-on-disk for Claude Code, coexist with Locker)
- ADR-0003 (schema parity strategy — flatten Connectors, drop UNIQUE_ID prefixes, Owner as Person FK)
- `feedback-incremental-build-not-scaffold-first.md` (governs build sequencing in stages — Stage 1 → Stage 5)
- `feedback-simplify-first.md` (rejected hybrid in favor of pure as the simpler stage-1 substrate)
