# ADR-0002: SQLite for Phase 1 Skill Vault

**Date:** 2026-03-02
**Status:** Accepted

## Context
The skill vault stores encrypted proprietary skills on corporate infrastructure. We needed a database for Phase 1 that matches the on-prem deployment story and minimizes operational complexity.

Primary developer has minimal database experience. Phase 1 targets single-machine deployments with admin-only writes.

## Decision
Use SQLite for the Phase 1 skill vault. Migrate to PostgreSQL when multi-user concurrency or horizontal scaling is needed.

## Consequences
**Easier:**
- Zero setup — SQLite is a single file, no server process to manage or configure
- Fits the on-prem value prop naturally: "your skills live in a file on your machine"
- Simple backup story: copy one file
- Lower barrier for developer with minimal DB experience
- Easy to bundle inside the Docker container

**Harder:**
- SQLite handles concurrent writes poorly — acceptable now (admin-only writes, single machine), becomes a problem when multiple admins write simultaneously or when running multi-instance deployments
- Migration to Postgres will require schema work — mitigate by writing clean SQL from day one (no SQLite-specific syntax)

## Migration trigger
Switch to PostgreSQL when any of the following is true:
- Multiple simultaneous admin users editing skills
- Deploying across multiple machines that share one vault
- Audit logging generates high-frequency writes

## Alternatives considered
**PostgreSQL from day one:** Production-grade, handles concurrency, better indexing. Rejected for Phase 1 because it requires running a separate server process, adds setup friction for first deployment, and the concurrency limitation doesn't apply at Phase 1 scale.

**MongoDB:** Document model could fit skill objects well. Rejected due to lack of familiarity and no strong advantage over SQLite at this scale.
