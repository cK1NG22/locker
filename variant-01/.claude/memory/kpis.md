# KPIs — Locker variant-01

Inherits the comparison-axis KPIs from `hub-mock-cos.md` Phase B2 (navigation latency, search accuracy, relation traversal) — applied here against the Supabase substrate instead of Notion.

## Stage gates (binary)

- [ ] **Stage 1 verify GREEN** — `python3 scripts/stage_1_verify.py` shows 5/5 RLS tests pass (including the negative cases that prove agents *cannot* mutate). BLOCKED on Carter Supabase dashboard work.
- [ ] **Stage 2 verify GREEN** — resources table + RLS, agent can read but not write.
- [ ] **Stage 3 verify GREEN** — skills table + sync-on-disk script + first end-to-end skill sync via `SessionStart` hook.
- [ ] **Stage 4 verify GREEN** — projects table + tasks gap closed (when triggered per ADR-0003).
- [ ] **Stage 5 verify GREEN** — real Optimal AI data migration; check constraints applied to vocab columns based on Adam's then-current live production.

## Dogfood adoption (qualitative until measurable)

- [ ] At least one skill autoloads in Claude Code from a Supabase row (proves sync-on-disk works end-to-end).
- [ ] Carter uses the variant for at least one real Optimal AI workflow over a week without falling back to Notion COS.
- [ ] Adam can read variant-01 data (via his own JWT) — proves multi-principal RLS works.
