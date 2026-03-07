# Skill Orchestrator Guide

The **Skill Orchestrator** is the person (or people) responsible for managing skills across an organization in Locker. This is typically a team lead, engineering manager, or ops role.

## Responsibilities

- **Create and maintain skills** — Write clear, reusable instructions that AI assistants follow. Keep them focused on one task each.
- **Assign skills to teams** — Decide which teams need which skills. Not every team needs every skill.
- **Review feedback** — Monitor skill feedback from team members and iterate on skill content.
- **Manage team tokens** — Distribute tokens to new team members. Rotate tokens if a member leaves.
- **Set conventions** — Configure the org-level skill convention (e.g., `/l`, `/locker`) so everyone uses the same invocation pattern.

## Best Practices

1. **Name skills clearly** — Use lowercase-hyphenated names that describe the task: `code-review`, `pr-description`, `test-plan`.
2. **Keep skills focused** — One skill per task. A skill that does three things should be three skills.
3. **Write for the AI, not the human** — Skills are instructions for the AI assistant. Be specific and imperative: "Always include..." not "You might want to..."
4. **Version through updates** — Edit existing skills rather than creating `skill-v2`. Teams always get the latest.
5. **Use descriptions** — Every skill should have a one-line description so team members know what it does without reading the full content.
6. **Audit regularly** — Check the usage dashboard to find unused skills (candidates for removal) and heavily-used skills (candidates for refinement).

## Org Structure

```
Organization (e.g., "Acme Corp")
├── Team: Engineering
│   ├── code-review
│   ├── pr-description
│   └── test-plan
├── Team: Legal
│   ├── contract-review
│   └── compliance-check
└── Team: Marketing
    ├── blog-draft
    └── social-post
```

Skills can be shared across teams within an org via share requests. The orchestrator initiates the request; the target team admin approves it.

## Getting Started

1. Create an org in the dashboard
2. Link your existing teams to the org
3. Set the skill convention (default: `/l`)
4. Upload skills and assign them to teams
5. Distribute team tokens to members via the companion link
