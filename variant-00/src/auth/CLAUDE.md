# src/auth/

FastAPI auth dependencies and Google OAuth endpoint.

## Files
- `__init__.py` — `require_user` dependency: validates `Authorization: Bearer <jwt>` header
- `jwt.py` — `create_token` / `decode_token` using PyJWT + LOCKER_JWT_SECRET env var
- `oauth.py` — `POST /api/v1/auth/google` endpoint: verifies Google ID token, upserts user, returns JWT

## Env vars required
- `LOCKER_JWT_SECRET` — secret key for signing JWTs (change from default in production)
- `GOOGLE_CLIENT_ID` — from Google Cloud Console OAuth credentials

## Rules
- Inject `require_user` into every admin route via Depends()
- Do NOT return raw skill content to unauthenticated requests
- Every signed-in Google user has full admin access (team-level roles come in task 3.2)
