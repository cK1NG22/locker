---
name: Locker v2 Unified Vision
description: Merged ContextOS + Locker product vision. AI-native firm meta-knowledge platform. Cloud-first SaaS, PWA, MCP Architecture 3, AI-first structuring, outcome-based pricing. Design doc approved 2026-04-06.
type: project
status: active
originSessionId: 53a52589-b6be-475e-9cf4-d9c06bb2e6a4
---
# Locker v2 — Unified Product Vision

**Approved:** 2026-04-06 via /office-hours
**Design doc:** `~/.gstack/projects/garrytan-gstack/carterking-main-design-20260406-143130.md`
**Test plan:** `~/.gstack/projects/garrytan-gstack/carterking-main-eng-review-test-plan-20260406-152500.md`
**DESIGN.md:** `~/.gstack/projects/garrytan-gstack/designs/DESIGN.md`
**Stitch mockups:** `https://stitch.withgoogle.com/projects/9095694389027193716` (6 screens)
**Plan file:** `~/.claude/plans/warm-humming-riddle.md`
**Design system:** "The Architectural Ledger" — dark spine #1a1a2e, warm paper #f9f9f9, blue CTA #4A6CF7, Inter Variable, No-Line Rule. Nexus purple palette explored and rejected.

**Reviews completed:** office-hours (8/10) → eng-review (CLEAR, 8 issues resolved) → design-review (2→8/10, 7 decisions) → design-consultation (DESIGN.md written)

## Strategic Origins

**Origin (2026-03-01):** Emerged from "Is there a way to build software that stores Claude skills but keeps them unviewable to users?" Core insight: companies worry about prompt/skill leakage to competitors, no enterprise solution exists for managing proprietary LLM instructions across teams.

**Original architecture vision:** Employee → Proxy → Skill Engine → Translation Layer (adapts per model) → API Router → Claude/GPT/Gemini → Response Filter → Employee.

**Key strategic insights:**
- Multi-model support requires only API connectors + translation layer (Claude prefers XML, GPT prefers markdown)
- Translation layer is the commercial moat: "write a skill once, it works everywhere"
- Response filter (detecting when LLM leaks injected instructions) is hardest unsolved component
- Skills are universal across LLMs — the enterprise management layer doesn't exist for any provider

## What it is

AI-native firm meta-knowledge platform. Stores how-tos, best practices, navigation guides, data structures, templates, codified processes, and skills. Other tools keep their data. Locker tells AI how to USE those tools effectively.

**Not** a replacement for Google Drive/Notion (in wedge phase). A knowledge LAYER alongside existing tools that structures content for AI consumption.

## Key decisions (locked 2026-04-06)

1. **Name:** Locker (kept). ContextOS vision is the core, Locker is the brand.
2. **Cloud-first SaaS.** PWA interface. New repo, fork useful Locker v1 patterns.
3. **AI-first structuring:** Users dump raw content → AI classifies/structures → human reviews/approves. No forms.
4. **MCP Architecture 3:** System context (L0 via MCP `instructions` field, always present) + peer MCP (detailed lookups via tools). Prioritized by value, not enforcement.
5. **Multiple content types:** Skills = one type among many. Universal schema in v1.
6. **Outcome-based + platform fee pricing.** Token savings dashboard as pricing justification.
7. **Beachhead:** Small-to-mid teams (5-50) via consultant channel (Adam) + self-serve.

## Phased roadmap

- **Phase 1 (3-4 weeks):** AI-Structured Wedge. Ingestion pipeline, review UI, MCP server, system prompt injection, analytics logging. FastAPI + React/Vite + Railway.
- **Phase 2 (6-8 weeks):** Orchestrator Agent. Auto-discovers knowledge in other tools (Google Drive, Salesforce). "I found 15 docs that look like SOPs."
- **Phase 3 (after 5+ customers):** Full Platform. Rich editor, multi-schema, RBAC, token savings dashboard.

## The assignment

Call Adam this week: "If I gave you a web app where you could paste your client's company processes, have AI structure them, and connect that to their Claude... would you deploy it at a client next month?"

## COS Integration (2026-04-07)

Adam shared a detailed COS (Context Operating System) PRD. Carter also has a separate repo with a working Outline-based COS: MCP wrapper (7 tools), Secret Vault RBAC, PR-style approvals, v0.7, 14 skills loaded.

**Relationship:** COS = engine (storage, MCP server, RBAC, content model, 7 agent tools), Locker = product (brand, PWA UI, pricing, analytics, AI pipeline, design system).

**Gap analysis:** Full comparison in plan file `~/.claude/plans/warm-humming-riddle.md`. Content types mapped, architecture compared, 10 PRD-only features and 8 Locker-only features identified.

**Decisions:**
- Storage: Outline now, migrate later (storage adapter). Changed from custom PostgreSQL.
- RBAC: Ships day 1 (Secret Vault already built in COS). Promoted from Phase 3.
- MCP tools: 7 COS tools (includes write-back) replace planned 4 read-only tools.
- Living system: `cos_log_preference` in v1 (like Claude's memory, stored in Locker). Automation later.
- AI ingestion: Manual via HITL Claude skill first. Automated pipeline deferred.
- Content taxonomy: COS collections + Locker types kept as separate dimensions. Reconcile later.

**COS tools (16 total from code review 2026-04-09):**
- Core (8): `cos_orient`, `cos_read_context`, `cos_list_skills`, `cos_load_skill`, `cos_execute_task`, `cos_log_preference` (partial), `cos_write_document`, `cos_get_project_status` (incomplete)
- Admin (4): `cos_list_users_admin`, `cos_create_user`, `cos_update_user`, `cos_deactivate_user`
- Governance (4): `cos_propose_change`, `cos_list_proposals`, `cos_get_proposal_detail`, `cos_resolve_proposal`

**COS repo status (2026-04-09):** `github.com/adamkingai/outline-mcp-server` (private fork of Vortiago/mcp-outline). Auth/RBAC production-ready. Tools ~70% complete. **Deployed and live.** Adam actively developing, eventual handoff to Carter. [Full code review](cos-repo-code-review.md)

**What Phase 1 becomes:** COS engine (built + deployed) + Locker PWA + analytics/token logging + HITL skill + system prompt injection. Faster than original plan since COS exists.

## Customer Feedback (Adam, 2026-03-12)

- **Team-level context docs:** Wants shared knowledge base (style guides, API docs, product specs) at the team level, not per-skill. Any skill can pull from it. Avoids duplication. → This is essentially what v2's AI-structured ingestion solves.
- **Access control:** Preferred doc-level blocking (skill works, restricted doc omitted) over skill-level blocking. But: defer access control until 50+ person teams. At 5-20 people, everyone sees everything. Do customer research at 5-10 paying teams first.
- **Onboarding:** Model after Dropbox — sign in and you're in. Invite link → Google sign-in → one command. No token-in-JSON. No scheduled key rotation (revoke-on-compromise instead).

## Supersedes

- [locker-context-os.md](locker-context-os.md) — original ContextOS concept (now merged)
- [project-merge-contextos-locker.md](project-merge-contextos-locker.md) — merge TODO (now done)
- [contextos-v0-architecture.md](contextos-v0-architecture.md) — v0 architecture (superseded by v2 design)
