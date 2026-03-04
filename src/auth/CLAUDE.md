# src/auth/

FastAPI dependency that validates the X-API-Key header against LOCKER_API_KEY env var.
Single function: `require_api_key`. Inject into every vault route.
Do NOT add per-user auth here — full RBAC is deferred to Phase 4.
