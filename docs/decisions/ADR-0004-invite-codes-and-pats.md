# ADR-0004: Team Invite Codes and Personal Access Tokens

**Date:** 2026-03-10
**Status:** Accepted

## Context
Teams shared a single UUID token for MCP access (`X-Team-Token`). This caused two problems:
1. **Confusing onboarding** — new members had to receive a long UUID from their admin, which is hard to share verbally or via chat.
2. **Fragile rotation** — rotating a compromised token broke every team member's MCP config simultaneously.

We needed per-user auth so removing one person doesn't affect anyone else, and a simpler onboarding code for joining teams.

## Decision
Two new mechanisms, with full backward compatibility:

### Invite codes
- Short, human-readable codes derived from the team name: `ACME-7X3K` (4 alpha chars + dash + 4 alphanumeric).
- Generated on team creation, stored in `teams.invite_code` (unique).
- Admins can regenerate via `POST /teams/{id}/regenerate-invite-code`.
- Members join via `POST /teams/join` with the code.

### Personal access tokens (PATs)
- Per-user tokens prefixed with `pat_` for clarity, stored as SHA-256 hashes in `user_tokens` table.
- Auto-generated on first team join if the user doesn't have one. Users can also create/revoke via `/me/tokens`.
- MCP clients send `X-User-Token` header instead of `X-Team-Token`.
- PAT resolves to user → user's teams → merged skills from all teams (deduped by skill ID).

### SSE context var convention
- The legacy MCP server passes auth via a `contextvars.ContextVar`. PAT tokens are stored with a `__pat__:` prefix (e.g. `__pat__:pat_abc123...`) to distinguish them from team tokens.
- The `_auth_headers()` helper parses this prefix and emits the correct HTTP header for internal API calls.

### Auth priority
- `X-User-Token` is checked before `X-Team-Token` everywhere (SSE handler, employee routes, feedback routes).
- If both headers are present, PAT wins.

### Backward compatibility
- `X-Team-Token` still works in all endpoints — existing setups are unaffected.
- No migration required for existing users. PATs are opt-in via dashboard or auto-created on team join.

## Consequences
- **Easier:** Onboarding — share a short code instead of a UUID. Offboarding — remove a member without breaking anyone else.
- **Harder:** Multi-team skill merging needs dedup logic (done, uses skill ID set). Convention/team name comes from the first team.
- **Different:** Two auth paths in every endpoint that accepts tokens. Unified via `_resolve_teams()` and `_auth_headers()` helpers to keep it DRY.

## Alternatives considered
1. **Magic links (email-based join)** — More friction (requires email delivery infra), overkill for small teams sharing codes over Slack.
2. **Scoped team tokens (one per member)** — Similar to PATs but tied to a single team. Rejected because PATs naturally support multi-team access.
3. **OAuth-only (no PAT)** — OAuth 2.1 path already exists (`/mcp/v2`) but requires browser flow. PATs work for headless CLI/MCP setups where OAuth is impractical.
