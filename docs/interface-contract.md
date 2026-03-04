# Locker — Interface Contract

**Version:** 2.0 (Phase 2 — Teams, Employee Endpoint, Companion Page)
**Status:** Locked for Phase 2 implementation

This document defines exactly how the five Locker components communicate. It is the
source of truth during build. When a route, shape, or behavior changes, update this
document first.

---

## Design Decisions

| Decision | Choice | Reason |
|---|---|---|
| Admin auth scheme | API key (`X-API-Key` header) | Simple, stateless, works for CLI + proxy + dashboard |
| Skill file format | Plain text (`.txt`) | Filename = skill name, content = skill text |
| Skill invocation model | Explicit (`/locker <name>`) in Phase 1; always-on in Phase 2 | Employees control which skills apply; admin controls which skills exist |
| Proxy caller identity | Blind interception | No per-user tracking in Phase 1 |
| LLM provider support | OpenAI, Anthropic, Google | Employees may use any of these tools; Locker intercepts all three |
| Service architecture | Single process, separate routers | Vault and proxy share one FastAPI app; clean boundaries allow splitting later |

---

## Skill Types

| Type | How it's triggered | Phase |
|---|---|---|
| On-demand | Employee types `/locker <skill-name>` in their message | Phase 1 |
| Always-on | Auto-injected silently into every session | Phase 2 |

Skills may need model-specific variants (same workflow tuned for Claude vs. GPT vs. Gemini).
A translation layer for this is planned but not Phase 1.

---

## 1. Vault API (Admin CRUD)

All routes require the header:

```
X-API-Key: <value of LOCKER_API_KEY env var>
```

Requests missing or with a wrong key receive `401 Unauthorized`.

### Routes

#### `POST /api/v1/skills` — Create a skill

Request body:
```json
{
  "name": "string",
  "content": "string",
  "description": "string (optional — visible to employees)"
}
```

Response `201 Created`:
```json
{
  "id": "string",
  "name": "string",
  "created_at": "ISO 8601 timestamp"
}
```

---

#### `GET /api/v1/skills?name={name}` — Lookup a skill by name (proxy use)

Query parameter `name` is optional. When provided, returns a single skill with decrypted content.
Used by the proxy when it detects `/locker <skill-name>` — fetches only the needed skill.

Response `200 OK`:
```json
{
  "id": "string",
  "name": "string",
  "content": "string",
  "created_at": "ISO 8601 timestamp",
  "updated_at": "ISO 8601 timestamp"
}
```

Response `404 Not Found` if name does not exist.

---

#### `GET /api/v1/skills` — List all skills (metadata only, no content)

Response `200 OK`:
```json
{
  "skills": [
    {
      "id": "string",
      "name": "string",
      "created_at": "ISO 8601 timestamp",
      "updated_at": "ISO 8601 timestamp"
    }
  ]
}
```

---

#### `GET /api/v1/skills/{id}` — Get one skill with content

Response `200 OK`:
```json
{
  "id": "string",
  "name": "string",
  "content": "string",
  "created_at": "ISO 8601 timestamp",
  "updated_at": "ISO 8601 timestamp"
}
```

Response `404 Not Found` if id does not exist.

---

#### `PUT /api/v1/skills/{id}` — Update a skill

Request body (all fields optional; at least one required):
```json
{
  "name": "string",
  "content": "string",
  "description": "string"
}
```

Response `200 OK`:
```json
{
  "id": "string",
  "name": "string",
  "updated_at": "ISO 8601 timestamp"
}
```

---

#### `DELETE /api/v1/skills/{id}` — Delete a skill

Response `204 No Content`

Response `404 Not Found` if id does not exist.

---

#### `GET /api/v1/skills/bundle` — All skills with content

This route requires `X-API-Key`. Returns all skills with decrypted content.
Use `/api/v1/skills?name={name}` for single-skill lookup (preferred for on-demand injection).

Response `200 OK`:
```json
{
  "skills": [
    {
      "id": "string",
      "name": "string",
      "content": "string"
    }
  ]
}
```

---

## 2. Proxy API (Employee LLM Intercept)

Employees point their LLM tool's base URL at Locker once (IT/admin sets this up).
No auth is required from the employee side — the proxy runs as internal infrastructure.
Company-owned API keys (not employee keys) are stored in Locker's env vars and used to
call the real providers.

**How it works:** When an employee types `/locker <skill-name>` anywhere in their message,
the proxy detects it, fetches that skill from the vault, replaces the command text with
the skill content, and forwards the modified message to the LLM. The employee never sees
the skill content — it's injected silently.

There are three routes, one per LLM provider.

---

### Route 1 — OpenAI format

```
POST /proxy/openai/v1/chat/completions
```

**Employee configuration:** `OPENAI_BASE_URL=http://locker-server/proxy/openai`

**Covers:** Codex CLI, any OpenAI-compatible tool, Cursor (OpenAI mode)

**Injection mechanic:**
1. Scan the `messages` array for a user message containing `/locker <skill-name>`
2. Look up the named skill in the vault
3. Replace the `/locker <skill-name>` text in that message with the skill content
4. Forward the modified request to `api.openai.com`

**Filtering mechanic:**
1. Receive the response from OpenAI
2. Strip any literal skill content from `choices[0].message.content` (Phase 1: string match)
3. Return the filtered response to the employee's client

Response shape matches the standard OpenAI Chat Completions format.

---

### Route 2 — Anthropic format

```
POST /proxy/anthropic/v1/messages
```

**Employee configuration:** `ANTHROPIC_BASE_URL=http://locker-server/proxy/anthropic`

**Covers:** Claude Code CLI

**Injection mechanic:**
1. Scan the `messages` array for a user message containing `/locker <skill-name>`
2. Look up the named skill in the vault
3. Replace the `/locker <skill-name>` text in that message with the skill content
4. Forward the modified request to `api.anthropic.com`
   (forward the `anthropic-version` request header as-is)

**Filtering mechanic:**
1. Receive the response from Anthropic
2. Strip any literal skill content from `content[0].text` (Phase 1: string match)
3. Return the filtered response to the employee's client

---

### Route 3 — Google Gemini format

```
POST /proxy/google/v1beta/models/{model}:generateContent
```

**Employee configuration:** `GOOGLE_GENAI_BASE_URL=http://locker-server/proxy/google`

**Covers:** Gemini CLI

**Injection mechanic:**
1. Scan the `contents` array for a user part containing `/locker <skill-name>`
2. Look up the named skill in the vault
3. Replace the `/locker <skill-name>` text in that part with the skill content
4. Forward the modified request to `generativelanguage.googleapis.com`

**Filtering mechanic:**
1. Receive the response from Google
2. Strip any literal skill content from `candidates[0].content.parts[0].text` (Phase 1: string match)
3. Return the filtered response to the employee's client

---

## 3. Auth (`src/auth/`)

- **Environment variable:** `LOCKER_API_KEY`
- **Header name:** `X-API-Key`
- **Scope:** All vault routes (`/api/v1/skills/*`)
- **Implementation:** FastAPI dependency function injected into every vault route
- **Proxy access:** The proxy reads `LOCKER_API_KEY` from env directly to call vault routes
- **Dashboard access:** Admin enters the key in a login form; it is stored in
  `sessionStorage` for the browser session only. No server-side session exists.
- **Proxy routes:** No employee auth — proxy runs as internal infrastructure.

### Company-owned LLM keys

Stored in Locker's environment (never exposed to employees):

| Variable | Provider |
|---|---|
| `OPENAI_API_KEY` | OpenAI |
| `ANTHROPIC_API_KEY` | Anthropic |
| `GOOGLE_API_KEY` | Google Gemini |

---

## 4. CLI (`locker deploy`)

### Command

```
locker deploy <skill-file.txt>
```

### Behavior

| Step | Action |
|---|---|
| 1 | Read `LOCKER_API_KEY` and `LOCKER_VAULT_URL` from environment or `.env` file |
| 2 | Derive skill name from filename (strip `.txt` extension) |
| 3 | Read file contents as skill content (plain text) |
| 4 | `POST /api/v1/skills` with `{ name, content }` and `X-API-Key` header |
| 5 | On success: print `Deployed skill "<name>" (id: <id>)` |
| 6 | On error: print HTTP status + error message, exit with code `1` |

### Environment variables

| Variable | Purpose |
|---|---|
| `LOCKER_API_KEY` | Admin key sent in `X-API-Key` header |
| `LOCKER_VAULT_URL` | Base URL of the running Locker service (e.g. `http://localhost:8000`) |

---

## 5. Dashboard

- Calls all vault CRUD routes (`/api/v1/skills/*`)
- Passes `X-API-Key: <key>` header on every request
- Key source: admin login form, stored in `sessionStorage` (cleared on tab close)
- No server-side session — fully stateless from the server's perspective

---

## 6. Team Management API (Admin)

All routes require `X-API-Key` header (admin only).

### Routes

#### `POST /api/v1/teams` — Create a team

Request body:
```json
{ "name": "string" }
```

Response `201 Created`:
```json
{ "id": "string", "name": "string", "token": "string (UUID)", "created_at": "ISO 8601" }
```

---

#### `GET /api/v1/teams` — List all teams

Response `200 OK`:
```json
[
  { "id": "string", "name": "string", "skill_count": 0 }
]
```

---

#### `GET /api/v1/teams/{id}` — Team detail with assigned skill names

Response `200 OK`:
```json
{ "id": "string", "name": "string", "token": "string", "created_at": "ISO 8601", "skills": ["skill-name-1"] }
```

---

#### `PUT /api/v1/teams/{id}` — Rename team

Request: `{ "name": "New Name" }` → Response: `TeamOut`

#### `DELETE /api/v1/teams/{id}` — Delete team (cascades skill assignments)

Response `204 No Content`

#### `PUT /api/v1/teams/{id}/skills` — Set skills for team

Request: `{ "skill_ids": ["uuid1", "uuid2"] }` → replaces all assignments.

---

## 7. Employee Skills API (No Admin Key Required)

Auth: `X-Team-Token` header (looked up against `teams.token`).

#### `GET /api/v1/employee/skills` — List skills for employee's team

Response `200 OK`:
```json
{
  "team": "Legal",
  "skills": [
    { "name": "legal-brief", "description": "Generates structured legal brief" },
    { "name": "contract-review", "description": null }
  ]
}
```

Response `401 Unauthorized` if token is invalid or missing.

Returns `name` + `description` only. Never returns skill content.

---

## 8. Companion Web Page

- Served as static files from the same Docker container at `/companion`
- Built with React + Tailwind + Vite, outputs to `static/companion/`
- Employees open `http://locker.company.com/companion` in any browser
- Token stored in `localStorage` (persists per-device)
- Auto-refreshes skill list every 30 seconds
- Copy-to-clipboard: copies `/locker <skill-name>` for pasting into LLM tools

---

## 9. CLI Updates

### `locker deploy` — Deploy a skill

```
locker deploy <skill-file.txt> [--description "Skill description"]
```

The `--description` (`-d`) flag sets the optional description visible to employees
in the companion page.

---

## What Comes Next

- **Phase 3:** Optional Electron wrapper for always-on-top companion window
- **Phase 3:** `locker team create` / `locker team assign` CLI commands for team management
- **Phase 4:** Admin dashboard (React + Tailwind) for visual skill + team management
- **Phase 4:** Full RBAC, audit logging, hashed team tokens + rate limiting
