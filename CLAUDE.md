# Locker — Variant Repository

This repo houses multiple Locker variants for comparison. Restructured from single-codebase into variant-00 / variant-01 on 2026-04-29 (see commit `f3a302c` for pre-restructure snapshot, tag `pre-variant-restructure` for rollback).

## Variants

- **`variant-00/`** — Original Locker MCP-fronted skills distribution (FastAPI + Postgres on Railway). The "Dropbox for AI Skills" build. See `variant-00/CLAUDE.md` for full product spec.
- **`variant-01/`** — Supabase-as-COS-substrate, agent-as-principal (Optimal AI dogfood). Migrated from `~/Projects/mock-cos/scripts/` + Supabase ADRs on 2026-04-29. See `variant-01/CLAUDE.md` for scope rules.

## Working in this repo

- **Always work inside a variant directory.** Don't add code or docs at the repo root other than this file.
- **Each variant is self-contained.** No imports across variants. They exist for comparison, not composition.
- **Variant-00 still ships to Railway + Vercel.** Don't break the deploy when reorganizing.
- **Variant-01 is gated.** Stage 1 of the Supabase build is BLOCKED on Carter creating the Supabase project in the dashboard. Don't unblock or run Stage 1 from this restructure work.

## Hub

Project hub: `~/.claude/projects/-Users-carterking/memory/hub-locker.md` (renamed from `hub-locker-v2.md` on 2026-04-29 to retire the v1/v2 framing in favor of variants).
