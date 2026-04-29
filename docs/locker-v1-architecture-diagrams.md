---
name: locker-architecture-diagrams
description: Three ASCII diagrams — system architecture, user roles/access matrix, and skill lifecycle flow for the Locker product
type: project
---

## Diagram 1: System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          LOCKER SYSTEM ARCHITECTURE                        │
└─────────────────────────────────────────────────────────────────────────────┘

  ┌───────────────────────┐         ┌──────────────────────────────────────┐
  │      VERCEL            │         │           RAILWAY                    │
  │  (Next.js Frontend)    │         │  (FastAPI Backend)                   │
  │                        │  HTTPS  │                                      │
  │  • Dashboard (admin)   │────────▶│  • /api/v1/*    (REST routes)        │
  │  • Invite flow         │  JWT /  │  • /mcp         (SSE, team/PAT)     │
  │  • Setup page          │  API key│  • /mcp/v2      (OAuth 2.1)         │
  │  • Companion (viewer)  │◀────────│  • /proxy       (Anthropic proxy)   │
  └───────────┬────────────┘         │                                      │
              │                      │  ┌──────────────────────────────┐    │
              │                      │  │  PostgreSQL                   │    │
              │                      │  │  (AES-256 encrypted at rest) │    │
              │                      │  │  skills, teams, orgs,        │    │
              │                      │  │  feedback, usage, oauth      │    │
              │                      │  └──────────────────────────────┘    │
              │                      └──────┬──────────────┬───────────────┘
              │                             │              │
              │                             │              │
    ┌─────────▼──────────┐                  │              │
    │   GOOGLE OAUTH     │                  │              │
    │                    │◀─────────────────┘              │
    │  • Admin sign-in   │   OAuth 2.0 (identity)         │
    │  • MCP v2 consent  │                                 │
    └────────────────────┘                                 │
                                                           │
         ┌─────────────────────┐          ┌────────────────▼──────────────┐
         │        CLI          │          │        AI TOOLS               │
         │  (locker command)   │          │  (Claude Code / Cursor)       │
         │                     │   HTTPS  │                               │
         │  • locker deploy    │─────────▶│  • /locker <skill> (via MCP)  │
         │  • locker sync      │  API key │  • list_skills                │
         │  • locker setup     │          │  • fetch_skill                │
         │                     │          │  • submit_feedback            │
         └─────────────────────┘          │                               │
                                          │  Auth: X-User-Token (PAT)    │
                                          │     or X-Team-Token (legacy)  │
                                          └───────────────────────────────┘
```

**Legend:**
- Arrows show direction of requests
- Auth methods labeled on each connection
- Admin routes accept `X-API-Key` header OR `JWT Bearer` token
- Employee/MCP routes accept `X-User-Token` (PAT, preferred) or `X-Team-Token` (legacy)
- MCP v2 uses full OAuth 2.1 with PKCE + Google sign-in consent


## Diagram 2: User Roles & Access Matrix

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        USER ROLES & ACCESS MATRIX                          │
├────────────────────────┬──────────┬──────────┬──────────┬──────────┬───────┤
│ ACTION                 │ Org      │ Team     │ Team     │ Employee │ Visi- │
│                        │ Admin    │ Admin    │ Member   │ (MCP)    │ tor   │
├────────────────────────┼──────────┼──────────┼──────────┼──────────┼───────┤
│ SKILLS                 │          │          │          │          │       │
│ Create / edit skill    │    Y     │    Y     │    N     │    N     │   N   │
│ Delete skill           │    Y     │    Y     │    N     │    N     │   N   │
│ Set visibility         │    Y     │    Y     │    N     │    N     │   N   │
│ Deploy via CLI         │    Y     │    Y     │    N     │    N     │   N   │
│ View open skills       │    Y     │    Y     │    Y     │    Y     │   Y*  │
│ View shared skills     │    Y     │    Y     │  name    │  name    │   N   │
│ View hidden skills     │    Y     │    Y     │    N     │    N     │   N   │
│ Use hidden (via proxy) │    Y     │    Y     │    Y     │    Y     │   N   │
├────────────────────────┼──────────┼──────────┼──────────┼──────────┼───────┤
│ TEAMS                  │          │          │          │          │       │
│ Create team            │    Y     │    N     │    N     │    N     │   N   │
│ Edit team settings     │    Y     │    Y     │    N     │    N     │   N   │
│ Generate invite code   │    Y     │    Y     │    N     │    N     │   N   │
│ Regenerate invite code │    Y     │    Y     │    N     │    N     │   N   │
├────────────────────────┼──────────┼──────────┼──────────┼──────────┼───────┤
│ MEMBERS                │          │          │          │          │       │
│ Add / remove members   │    Y     │    Y     │    N     │    N     │   N   │
│ View member list       │    Y     │    Y     │    N     │    N     │   N   │
│ Join via invite code   │    N     │    N     │    Y     │    —     │   Y   │
├────────────────────────┼──────────┼──────────┼──────────┼──────────┼───────┤
│ ORGS                   │          │          │          │          │       │
│ Create org             │    Y     │    N     │    N     │    N     │   N   │
│ Manage org settings    │    Y     │    N     │    N     │    N     │   N   │
│ Cross-team share req   │    Y     │    Y†    │    N     │    N     │   N   │
│ View org analytics     │    Y     │    N     │    N     │    N     │   N   │
├────────────────────────┼──────────┼──────────┼──────────┼──────────┼───────┤
│ FEEDBACK               │          │          │          │          │       │
│ Submit feedback        │    Y     │    Y     │    Y     │    Y     │   N   │
│ View feedback queue    │    Y     │    Y     │    N     │    N     │   N   │
│ Resolve feedback       │    Y     │    Y     │    N     │    N     │   N   │
├────────────────────────┼──────────┼──────────┼──────────┼──────────┼───────┤
│ MCP                    │          │          │          │          │       │
│ Connect via PAT        │    Y     │    Y     │    Y     │    Y     │   N   │
│ Connect via team token │    Y     │    Y     │    Y     │    Y     │   N   │
│ Connect via OAuth 2.1  │    Y     │    Y     │    Y     │    Y     │   N   │
│ Use fetch_skill        │    Y     │    Y     │    Y     │    Y     │   N   │
│ Use list_skills        │    Y     │    Y     │    Y     │    Y     │   N   │
│ Use submit_feedback    │    Y     │    Y     │    Y     │    Y     │   N   │
└────────────────────────┴──────────┴──────────┴──────────┴──────────┴───────┘

 *  Visitor sees open skills on companion page only (no auth required)
 †  Team Admin can request share; Org Admin can approve
    "name" = name + description only (no content)
    "—"   = not applicable for that role
```


## Diagram 3: Skill Lifecycle Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          SKILL LIFECYCLE FLOW                              │
└─────────────────────────────────────────────────────────────────────────────┘

 ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌─────────┐
 │ 1.CREATE │───▶│ 2.ASSIGN │───▶│ 3.CONNECT│───▶│ 4.FETCH  │───▶│5.REFINE │
 └────┬─────┘    └────┬─────┘    └────┬─────┘    └────┬─────┘    └────┬────┘
      │               │               │               │               │
      ▼               ▼               ▼               ▼               ▼
┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────────┐ ┌───────────┐
│ Dashboard │  │ Admin     │  │ Employee  │  │ AI Tool runs  │ │ Employee  │
│  or CLI   │  │ assigns   │  │ runs:     │  │ /locker <name>│ │ submits   │
│  upload   │  │ skill to  │  │           │  │               │ │ feedback  │
│           │  │ team(s)   │  │ locker    │  │ MCP calls     │ │ via MCP   │
│ Skill     │  │           │  │  setup    │  │ fetch_skill   │ │           │
│ content   │  │ Sets      │  │           │  │               │ │ "Output   │
│ encrypted │  │ visibility│  │ Gets MCP  │  │ Server:       │ │  looked   │
│ AES-256   │  │ per skill:│  │ config +  │  │ • decrypt     │ │  like X   │
│ stored in │  │           │  │ PAT auto- │  │ • check vis   │ │  because  │
│ PostgreSQL│  │ • open    │  │ written   │  │ • return      │ │  Y, fix:  │
│           │  │ • shared  │  │ to claude │  │   content     │ │  Z"       │
│ + ref     │  │ • hidden  │  │ config    │  │               │ │           │
│   files   │  │           │  │           │  │ Visibility:   │ │ Identity  │
│   (opt)   │  │           │  │ OR: join  │  │ open → full   │ │ stored    │
│           │  │           │  │ via invite│  │ shared → stub │ │ separately│
│           │  │           │  │ code      │  │ hidden → auto │ │ (privacy) │
└───────────┘  └───────────┘  └───────────┘  └───────────────┘ └─────┬─────┘
                                                                     │
                              ┌───────────────────────────────────────┘
                              ▼
                    ┌───────────────────┐     ┌───────────────────┐
                    │  Admin reviews    │────▶│  Skill updated    │
                    │  feedback queue   │     │  (new version)    │
                    │  in dashboard     │     │  ───────────────  │
                    │                   │     │  Employees get    │
                    │  Can resolve,     │     │  latest on next   │
                    │  dismiss, or      │     │  fetch_skill call │
                    │  act on feedback  │     └───────────────────┘
                    └───────────────────┘
                                                      │
                                              ┌───────▼───────┐
                                              │  Cycle repeats │
                                              │  (back to 4)   │
                                              └───────────────┘
```

**Legend:**
- Steps 1-2 are admin actions (dashboard or CLI)
- Step 3 is a one-time employee setup
- Steps 4-5 repeat continuously during daily use
- Encryption/decryption is transparent — admins and employees never see it
- Feedback submitter identity is stored separately from feedback text (privacy)
