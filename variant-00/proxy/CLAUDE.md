# proxy/

LLM API call interceptor. This is the core product.

## Purpose
Sits in the critical path of every outbound LLM call. Receives the request, queries the
vault for relevant skills, injects them into the request, forwards to the LLM provider,
and strips raw skill content from the response before returning it to the caller.

## Key files (to be created)
- `main.py` — FastAPI app entrypoint
- `injector.py` — Skill injection logic (fetches from vault, merges into request)
- `filter.py` — Response filtering (strips skill content before returning to caller)

## Rules
- NEVER return raw skill content to non-admin callers — filter.py is the enforcement point
- Depends on `vault/` and `src/auth/` being stable before this component is built
- Tests go in `tests/test_proxy.py` (unit + integration)
