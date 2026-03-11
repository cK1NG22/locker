# Locker — Product Specification

## Overview
Locker is enterprise middleware for distributing AI coding skills across teams via the Model Context Protocol (MCP). Teams deploy skills once and every member gets them automatically in their AI coding assistant — no manual copying, no version drift.

## Target User
Team leads and engineering managers at 5–50 person firms using AI coding assistants (Claude Code, GitHub Copilot, Cursor). They need a way to share prompt-engineering knowledge without emailing markdown files or maintaining shared drives.

## Value Proposition
"Dropbox for AI Skills" — upload a skill to Locker, assign it to a team, and every member can invoke it instantly from their terminal. Skills stay encrypted at rest, usage is tracked, and feedback flows back to authors.

## Tech Stack
- **Backend:** FastAPI (Python) — async, lightweight, auto-generated OpenAPI docs
- **Frontend:** Next.js 16 + Tailwind CSS — hosted on Vercel
- **Database:** PostgreSQL — hosted on Railway
- **Auth:** Google OAuth 2.0 + JWT + team tokens + personal access tokens
- **Protocol:** MCP (Model Context Protocol) — SSE transport for real-time skill delivery
- **Encryption:** AES-256 via Python `cryptography` library
- **Hosting:** Railway (backend + DB) + Vercel (frontend)

## Key Architecture Decisions
1. **MCP over REST** — Skills are consumed inside AI coding assistants, which natively support MCP. REST would require a custom client; MCP integrates with zero code on the consumer side.
2. **AES-256 encryption at rest** — Firm IP stored as skills must be protected. Encryption ensures database compromise doesn't expose proprietary knowledge.
3. **Three visibility levels** (hidden / shared / open) — Gives admins granular control over which skills are discoverable vs. pushed vs. invisible to non-admins.
4. **Railway + Vercel split** — Backend needs persistent connections (SSE, DB pooling); Railway handles that well. Frontend is static/SSR; Vercel is faster and free-tier friendly.
5. **Google OAuth + invite codes** — Low-friction onboarding. New members join via invite link, sign in with Google, and are immediately on the team.

## Live URLs
- **Backend:** https://locker.up.railway.app
- **Frontend:** https://locker-ui-three.vercel.app
- **MCP endpoint:** https://locker.up.railway.app/mcp
- **Health check:** https://locker.up.railway.app/health
