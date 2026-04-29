# ADR-0001: FastAPI for the Proxy Server

**Date:** 2026-03-02
**Status:** Accepted

## Context
The proxy server sits in the critical path of every LLM call — it intercepts requests, injects skills, and filters responses. It needs to handle concurrent requests without blocking. We needed to choose a backend framework.

Primary developer is comfortable with Python and has limited Node/TypeScript experience.

## Decision
Use FastAPI (Python) for the proxy server and all backend services.

## Consequences
**Easier:**
- Async request handling out of the box — important for a proxy that awaits multiple LLM API calls
- Automatic OpenAPI docs generated from type hints — useful when demoing to enterprise IT buyers
- Python `cryptography` library integrates naturally for skill vault encryption
- No context-switching between Python backend and JS frontend

**Harder:**
- Frontend (React) and backend (Python) are different languages — no code sharing between them
- Python deployment in Docker is slightly heavier than Node

## Alternatives considered
**Node.js / Express:** Same language as the React dashboard, large ecosystem. Rejected because the developer is less comfortable with TypeScript, and learning a new language while building security-critical proxy logic adds unnecessary risk.

**Node.js / Fastify:** Higher performance than Express, but same language concern applies. Rejected for same reason.
