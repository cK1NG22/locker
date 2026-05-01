# Skills Registry Inventory — Supabase Migration Readiness

**Date**: 2026-04-27  
**Scope**: All active skills in `~/.claude/skills/` (65 directories; excludes `_archived/`)  
**Ordering**: Best-to-worst migration candidates (small + prompt-only + Optimal-internal first)

| Slug | Name | Kind | Scope | Size | Lines | Dependencies | Flags |
|------|------|------|-------|------|-------|--------------|-------|
| **locker** | Locker Skill Router | prompt-only | team | small | 19 | Locker MCP | **BEST CANDIDATE**: tiny, router to team server, no body logic |
| **api-design** | API Design Principles | prompt-only | global | small | 36 | None | Generic reference; broad trigger risk |
| **unfreeze** | Unfreeze | prompt-only | global | small | 40 | None | Complement to freeze; minimal logic |
| **opusplan** | Opus Plan | prompt-only | global | small | 74 | Claude API (Opus) | Plan generator, lightweight |
| **freeze** | Freeze Edits | prompt-only | global | small | 82 | Bash (hook-based) | File boundary enforcement; hooks in settings |
| **guard** | Guard | prompt-only | global | small | 82 | Bash | Safety guardrails, generic |
| **careful** | Careful | prompt-only | global | small | 59 | Bash | Destructive command warnings |
| **memory-review** | Memory Review | prompt-only | personal | small | 88 | Carter's memory files | Carter-specific but Optimal context |
| **skill-creator** | Skill Creator | tool-bearing | team | medium | 497 | Scripts (eval runners) | **Core migration candidate** for skill authoring |
| **skill-compliance** | Skill Compliance | tool-bearing | team | small | 148 | Scripts | Audit tool; Optimal internal |
| **mcp-builder** | MCP Server Guide | tool-bearing | global | medium | 236 | Scripts, reference files | MCP protocol docs; reference materials |
| **skill-spec-validator** | Skill Spec Validator | prompt-only | team | small | 160 | Skill Factory, spec validation | Optimal internal validator |
| **new-project** | New Project | prompt-only | global | small | 121 | Scaffold logic | Project initialization |
| **new-session** | New Session | prompt-only | global | small | 164 | Handoff logic | Session continuity |
| **close-session** | Close Session | prompt-only | global | medium | 215 | Read, Edit | End-of-session capture |
| **sources-cited** | Sources Cited | prompt-only | global | small | 120 | Research tracking | Bibtex/reference manager |
| **kpi-setter** | KPI Setter | prompt-only | team | small | 150 | Process mapping | Optimal internal workflow |
| **dung** | Parallel Worktree | prompt-only | global | small | 151 | Bash (orchestrator) | Vendored gstack worktree tool |
| **connect-vault** | Connect Vault | prompt-only | team | small | 141 | Notion wikilinks | Optimal internal, resource linking |
| **github-digest** | GitHub Digest | prompt-only | global | medium | 303 | GitHub API | Daily trending harvester |
| **gstack-upgrade** | gstack Upgrade | prompt-only | global | small | 275 | gstack binary | Framework self-upgrade |
| **setup-browser-cookies** | Setup Browser Cookies | prompt-only | global | medium | 522 | Browser automation | Cookie import from Chrome |
| **discovery-call-prep** | Discovery Call Prep | prompt-only | personal | small | 128 | Web research | Prospect briefing; generic business |
| **tdd** | Test-Driven Dev | prompt-only | global | medium | 378 | Test runners | Methodology enforcer |
| **email-tracker** | Email Tracker | prompt-only | global | medium | 386 | Gmail parsing | Newsletter triage |
| **brain-dump** | Brain Dump | prompt-only | personal | small | 123 | Carter's memory files, Write | Thought organizer; Carter-scoped paths |
| **connect-chrome** | Connect Chrome | prompt-only | global | medium | 770 | Chrome extension | Headed browser control |
| **checkpoint** | Checkpoint | prompt-only | personal | medium | 813 | Session state, Write | Save/resume; project-specific |
| **gstack** | gstack Core | tool-bearing | global | large | 863 | Scripts, binaries | Framework hub; complex preamble |
| **investigate** | Investigate | prompt-only | global | medium | 775 | Debugging tools | Root cause analysis |
| **health** | Health | prompt-only | global | medium | 801 | Code quality runners | Quality dashboard |
| **learn** | Learn | prompt-only | global | medium | 707 | Learning trackers | Project learnings manager |
| **canary** | Canary | prompt-only | global | medium | 806 | Deployment monitors | Post-deploy watching |
| **setup-deploy** | Setup Deploy | prompt-only | global | medium | 735 | Deployment config | Config for /land-and-deploy |
| **design-html** | Design HTML | tool-bearing | global | large | 1180 | Scripts (design gen) | Production HTML generator |
| **document-release** | Document Release | prompt-only | global | medium | 925 | Doc updates | Post-ship doc sync |
| **qa-only** | QA Report | prompt-only | global | medium | 1009 | QA report runner | Report-only QA variant |
| **devex-review** | DevEx Review | prompt-only | global | medium | 1034 | Browse tool | Developer experience audit |
| **design-shotgun** | Design Shotgun | prompt-only | global | medium | 954 | Design variants gen | Multi-design exploration |
| **design-review** | Design Review | prompt-only | global | large | 1596 | Browse, visual QA | Designer's visual audit |
| **benchmark** | Benchmark | prompt-only | global | large | 673 | Perf regression testing | Performance detection |
| **autoresearch** | Autoresearch | prompt-only | global | medium | 199 | Research optimizer | Self-improving research |
| **architecture-review** | Architecture Review | prompt-only | global | medium | 176 | Code structure audits | Modern arch reviewer |
| **plan-eng-review** | Plan Eng Review | prompt-only | global | large | 1431 | Eng plan review | Eng manager mode |
| **browse** | Browse | tool-bearing | global | large | 744 | gstack/scripts | Headless browser; preamble-tier:1 |
| **doc-coauthoring** | Doc Coauthoring | prompt-only | global | medium | 375 | Structured workflow | Co-authoring guide |
| **claude-audit** | Claude Audit | prompt-only | global | medium | 296 | Claude Code setup audit | Framework audit |
| **review** | Review | prompt-only | global | large | 1467 | Pre-landing review | PR review workflow |
| **retro** | Retro | prompt-only | global | large | 1467 | Commit analyzer | Weekly retrospective |
| **qa** | QA | prompt-only | global | large | 1419 | QA test runner | Full QA workflow |
| **codex** | Codex | prompt-only | global | large | 1075 | gstack/OpenAI CLI | Code review via Codex; preamble-tier:3 |
| **cso** | CSO | prompt-only | global | large | 1225 | Infra-first security | Security mode; large scope |
| **land-and-deploy** | Land Deploy | prompt-only | global | large | 1586 | Git + test runners | Merge/test/deploy workflow |
| **plan-design-review** | Plan Design Review | prompt-only | global | large | 1529 | Design plan review | Designer's interactive review |
| **autoplan** | Autoplan | prompt-only | global | large | 1464 | Plan review pipeline | Auto-review full pipeline |
| **design-consultation** | Design Consultation | prompt-only | global | large | 1265 | Product + research | Design thinking guide |
| **plan-ceo-review** | Plan CEO Review | prompt-only | global | large | 1837 | Strategy rethink | CEO/founder mode |
| **open-gstack-browser** | Open gstack Browser | prompt-only | global | medium | 770 | GStack Browser launcher | AI-controlled Chromium |
| **office-hours** | Office Hours | prompt-only | global | large | 1714 | Design doc generator | YC-style forcing Q's; preamble-tier:3 |
| **ship** | Ship | prompt-only | global | large | 2543 | Full deploy pipeline | Merge/test/version/changelog/deploy; preamble-tier:4 |
| **xlsx** | XLSX | tool-bearing | global | medium | 291 | Scripts | Spreadsheet automation |
| **pptx** | PPTX | tool-bearing | global | medium | 232 | Scripts | PowerPoint generation |
| **pdf** | PDF | tool-bearing | global | medium | 314 | Scripts | PDF processing |
| **docx** | DOCX | tool-bearing | global | medium | 467 | Scripts | Word doc generation |
| **database-design** | Database Design | tool-bearing | global | small | 57 | Scripts | Data modeling guide |
| **vercel-deploy-claimable** | Vercel Deploy | tool-bearing | global | small | 112 | Scripts | Vercel deployment |
| **ui-ux-pro-max** | UI/UX Pro Max | tool-bearing | global | medium | 386 | Scripts | Design intelligence |
| **acme-board-memo** | ACME Board Memo | tool-bearing | personal | small | 58 | Scripts | Board memo docgen |
| **411-research** | 411 Research | prompt-only | global | medium | 216 | SIFT methodology | Structured research |
| **411-refine** | 411 Refine | prompt-only | global | medium | 220 | Research output verify | Re-refine research |
| **411-reresearch** | 411 Reresearch | prompt-only | global | medium | 181 | Targeted re-research | Failed source targeting |
| **411-case** | 411 Case | tool-bearing | global | medium | 189 | Scripts (case analysis) | Business case analyzer |
| **411-deck** | 411 Deck | prompt-only | global | medium | 200 | Deck generator | Structured presentation |

## Migration Readiness Summary

### Best Candidates (Small + Prompt-only + Team/Internal)
- **locker** (19 lines) - router to Locker MCP; dependency already exists
- **skill-creator** (scripts) - core Optimal authoring tool
- **skill-compliance** (scripts) - audit companion for skill-creator
- **skill-spec-validator** (160 lines) - validation gate for Optimal workflows

### Don't Migrate (Cart-specific paths, file I/O)
- **brain-dump** (hardcoded `~/.claude/projects/-Users-carterking/memory/`)
- **checkpoint** (session state, project-specific resume logic)
- **memory-review** (Carter's memory index)
- **acme-board-memo** (Acme/personal context)
- **discovery-call-prep** (prospect-specific)

### Problematic for Cursor Round-trip
All **tool-bearing** skills (12 total) fail Cursor's prompt-only format. Notable:
- **gstack** family (browse, codex, ship, office-hours) — require preamble + binaries
- **docx/xlsx/pdf/pptx** — document generation; require scripts
- **design-html** — production design markup generation

### Duplicates / Consolidation Candidates
- **qa** + **qa-only** → merge into one with mode flag
- **plan-ceo-review** + **plan-eng-review** + **plan-devex-review** → one skill, mode parameter
- **design-review** + **design-shotgun** + **design-html** → design pipeline stages

### Weakly-Specified Autoload Risks
- **api-design** (generic name "principles")
- **brain-dump** (semantic overload: "drop thoughts", "save ideas", "organize notes")
- **new-session** / **close-session** (broad lifecycle triggers)

---

## Recommendations for ADR-0002 (formerly mock-cos ADR-0009)

1. **Stage 1 payload**: Migrate **locker** as proof of concept (router pattern is clean).
2. **Stage 5 (real data)**: Selective sync of `kind='prompt-only'` skills only (excludes gstack family, document generators).
3. **Deferred**: MCP-server variant for tools/external clients; Cursor adapter (round-trip losses documented).
4. **Coexistence rule**: Locker + Supabase sync serve different purposes — team-managed (Locker) vs personal/internal (Supabase).

