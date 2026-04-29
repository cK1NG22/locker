---
name: ContextOS Build vs. Buy vs. Design Decisions
description: Full list of strategic, purchasing, build, and deferred decisions for ContextOS. Use when scoping roadmap, choosing vendors, or deciding what to prioritize. Updated 2026-03-19.
type: project
---

# ContextOS — Decisions Roadmap

*Developed 2026-03-19.*

---

## DESIGN Decisions (you decide the strategy)

### Product & UX
- [ ] What does the UI look like? Editor? File manager? Wiki-style? Obsidian-style graph view?
- [ ] Who creates and maintains content — humans only, AI-assisted, or fully automated?
- [ ] What happens when content goes stale? Who gets notified? How does it get retired?
- [ ] How opinionated are structure templates? Fully customizable or constrained to template?
- [ ] What's the onboarding flow for a new company? (How do they get their first 50 docs in?)

### Data Model
- [ ] What are the exact L0/L1/L2 generation rules? (Agent, human, or hybrid writes them?)
- [ ] What entity types go in the knowledge graph? Controlled vocabulary or LLM-determined?
- [ ] How does deduplication work? Exact match? Semantic similarity? Who resolves conflicts?
- [ ] What does "staleness" mean? Time-based? Edit-based? Usage-based?

### Business Model
- [ ] Open-source core + paid hosting (MongoDB model) OR fully proprietary?
- [ ] Pricing: per seat, per storage, per API call, or flat enterprise contract?
- [ ] When to add self-hosted/private-cloud deployment? Day one or after enterprise demand?

---

## PURCHASING Decisions (third-party tools to license)

| Decision | Options | What it affects |
|----------|---------|----------------|
| **AI model for L0/L1 generation** | Claude API, GPT-4o, Gemini | Quality of auto-generated summaries |
| **AI model for NER/entity extraction** | Claude, GPT-4o, spaCy (free) | Quality of auto-linking in Phase 3 |
| **Document chunking** | Unstructured.io (paid), LlamaIndex (free) | Phase 2 L2 chunked retrieval |
| **Graph engine** | Cognee (open-source), Neo4j (enterprise) | Phase 3 GraphRAG layer |
| **Vector search** | pgvector (free Postgres), Pinecone (paid), Weaviate (open-source) | Semantic chunk search |
| **Auth / identity** | Auth0, Clerk, Supabase Auth | Login, SSO for enterprise |
| **File storage** | AWS S3, Cloudflare R2 | Where uploaded documents live |
| **Hosting** | Railway (current), AWS, Fly.io | Where the app runs |
| **Compliance certs** | SOC 2 via Vanta (~$7-15K/yr), HIPAA BAA | Enterprise sales prerequisite |

---

## BUILD Decisions (build from scratch or customize)

| Component | Complexity | Notes |
|-----------|-----------|-------|
| **Structure templates** | Low | Opinionated filing cabinet — core UX differentiator |
| **Ingestion pipeline** | Medium | Upload → auto-classify → L0/L1 generation → graph linking |
| **RBAC system** | Medium | Viewer/Editor/Publisher/Admin per workspace + per content type |
| **MCP delivery layer** | Medium | API that agents call to pull context from ContextOS |
| **Team collaboration** | Medium | Multi-user editing, approval workflows, version history |
| **UI / editor** | High | Content creation + browsing interface |
| **Self-hosted deployment** | High | Docker packaging, infra docs, enterprise IT onboarding |
| **Model routing** | High (Phase 3+) | Smart routing based on tier + task complexity |

---

## OUTSOURCE / DEFER (don't build these)

- Custom graph database — use Cognee or pgvector
- Custom NER model — use LLM-based extraction (Claude/GPT), don't train custom
- Custom chunking logic — Unstructured.io handles all doc types automatically
- Compliance certifications — defer until enterprise customers require it
- Self-hosted deployment — defer until a paying customer specifically requires it

---

## Architecture Phase Sequence

**Phase 1 (MVP):** L0/L1/L2 tiers + full-doc L2 (token cap ~10K) + MCP delivery + structure templates + RBAC + team collab
**Phase 2:** Chunked L2 via Unstructured.io + pgvector + Admin dashboard + token savings dashboard + dept admin roles
**Phase 3:** GraphRAG via Cognee — auto entity extraction, bidirectional linking, multi-hop retrieval + contradiction detection

---

## Feature-Level Decisions (locked 2026-03-20)

These decisions were made during the feature discovery process and should not be re-litigated without cause.

### Locked Decisions

| Decision | What was decided | Why |
|----------|-----------------|-----|
| Invisible-first | Employees never see ContextOS. Admins manage via dashboard. | Matches thesis: company provides context, not employees. Reduces adoption friction. |
| Admin hierarchy | Exec Admin (company-wide) + Dept Admins (domain-level). Flat RBAC in Phase 1. | Answers "who maintains the context?" Scales accountability without individual doc owners. |
| Live MCP sync | Ongoing sync, not one-time import. Full versioning. | Source tools stay system of record. Context must stay current without manual admin effort. |
| Exact delivery flag | Skills/scripts bypass L0/L1/L2 — delivered whole. | Some content cannot be summarized without losing fidelity (code, step-by-step processes). |
| Manual dedup approval | System detects, human approves resolution. | AI can flag but should not autonomously delete or merge content. |
| A8 deferred | Multi-hop retrieval is Phase 3+ after token efficiency is proven. | Risky to build before proving the value. Depends on GraphRAG anyway. |
| B3/B4 deferred | Verification workflows + trust scoring are future options. | Not needed for initial adoption. Adds complexity before product-market fit. |
| B5 after GraphRAG | Contradiction detection requires knowledge graph (A7). | Technical dependency — cannot scan relationships that don't exist yet. |
| B6 out of scope | Completeness scoring vs. other firms is not core business. | Comparative benchmarking is a different product. Avoid scope creep. |
| E7 in scope | Admin content management tools (reclassify, re-tier, bulk archive). | Dept admins need tools to actively manage their section, not just monitor. |
| E8 in scope | Token savings dashboard to quantify ROI. | "ContextOS saved $X this month" is a core sales pitch. Must be measurable. |

### Open Decisions (still need answers)

- [ ] What are the exact L0/L1/L2 generation rules? (Agent, human, or hybrid writes them?)
- [ ] What entity types go in the knowledge graph? Controlled vocabulary or LLM-determined?
- [ ] What does "staleness" mean exactly? Time-based? Edit-based? Usage-based?
- [ ] Open-source core + paid hosting OR fully proprietary?
- [ ] Pricing model: per seat, per storage, per API call, or flat enterprise contract?
- [ ] Which specific admin content management tools to build first (E7)?
- [ ] How opinionated are structure templates? Fully customizable or constrained?
