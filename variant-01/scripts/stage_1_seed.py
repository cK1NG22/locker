#!/usr/bin/env python3
"""Stage 1 seed — creates Optimal AI team + owner/agent memberships.

Prerequisites (per scripts/README.md):
    1. Supabase project created in dashboard
    2. .env populated and chmod 600
    3. 0001_schema.sql executed against the project
    4. Carter signed up via Supabase Studio (Authentication -> Users)
    5. cos-sync-agent signed up via Supabase Studio
    6. cos-sync-agent's app_metadata.role updated to 'agent' via SQL

Usage:
    cd ~/Projects/locker/variant-01/scripts
    python3 -m pip install supabase
    python3 stage_1_seed.py
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    from supabase import Client, create_client
except ImportError:
    print("Missing dependency: supabase. Install with `pip install supabase`.", file=sys.stderr)
    sys.exit(1)


def load_env() -> dict[str, str]:
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        print(f"Missing {env_path}. Copy .env.example to .env and fill in values.", file=sys.stderr)
        sys.exit(1)
    env: dict[str, str] = {}
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def main() -> None:
    env = load_env()
    required = [
        "SUPABASE_URL",
        "SUPABASE_SERVICE_ROLE_KEY",
        "OPTIMAL_OWNER_EMAIL",
        "COS_AGENT_EMAIL",
        "OPTIMAL_TEAM_NAME",
        "OPTIMAL_TEAM_SLUG",
    ]
    missing = [k for k in required if not env.get(k)]
    if missing:
        print(f"Missing env vars: {missing}", file=sys.stderr)
        sys.exit(1)

    # Service-role client bypasses RLS — required for first-time seeding.
    supabase: Client = create_client(env["SUPABASE_URL"], env["SUPABASE_SERVICE_ROLE_KEY"])

    # === Look up the two pre-created auth users by email ===
    print("Looking up users via admin API...")
    list_resp = supabase.auth.admin.list_users()
    # supabase-py 2.x returns a list of User objects; older versions wrap them.
    users = list_resp if isinstance(list_resp, list) else getattr(list_resp, "users", list_resp)

    users_by_email = {u.email: u for u in users}
    owner_email = env["OPTIMAL_OWNER_EMAIL"]
    agent_email = env["COS_AGENT_EMAIL"]

    if owner_email not in users_by_email:
        print(
            f"Owner {owner_email} not found in auth.users. "
            "Sign up via Supabase Studio (Authentication -> Users -> Add user) first.",
            file=sys.stderr,
        )
        sys.exit(1)
    if agent_email not in users_by_email:
        print(
            f"Agent {agent_email} not found in auth.users. "
            "Sign up via Supabase Studio first.",
            file=sys.stderr,
        )
        sys.exit(1)

    owner = users_by_email[owner_email]
    agent = users_by_email[agent_email]

    # === Verify the agent has app_metadata.role = 'agent' ===
    agent_meta = getattr(agent, "app_metadata", None) or {}
    agent_role = agent_meta.get("role") if isinstance(agent_meta, dict) else None
    if agent_role != "agent":
        print(
            f"Agent {agent_email} has app_metadata.role={agent_role!r}, expected 'agent'.\n"
            "Run this in Supabase SQL Editor:\n"
            "  update auth.users\n"
            "  set raw_app_meta_data = raw_app_meta_data || '{\"role\": \"agent\"}'::jsonb\n"
            f"  where email = '{agent_email}';",
            file=sys.stderr,
        )
        sys.exit(1)

    # === Idempotent team upsert by slug ===
    team_name = env["OPTIMAL_TEAM_NAME"]
    team_slug = env["OPTIMAL_TEAM_SLUG"]
    print(f"Ensuring team {team_name!r} (slug={team_slug!r})...")

    existing = supabase.table("teams").select("*").eq("slug", team_slug).execute()
    if existing.data:
        team = existing.data[0]
        print(f"  Team already exists: id={team['id']}")
    else:
        created = (
            supabase.table("teams")
            .insert({"name": team_name, "slug": team_slug})
            .execute()
        )
        team = created.data[0]
        print(f"  Team created: id={team['id']}")

    # === Idempotent memberships upsert ===
    print(f"Ensuring owner membership ({owner_email}, role=owner)...")
    supabase.table("memberships").upsert(
        {"user_id": owner.id, "team_id": team["id"], "role": "owner"},
        on_conflict="user_id,team_id",
    ).execute()

    print(f"Ensuring agent membership ({agent_email}, role=agent)...")
    supabase.table("memberships").upsert(
        {"user_id": agent.id, "team_id": team["id"], "role": "agent"},
        on_conflict="user_id,team_id",
    ).execute()

    print()
    print("=== Stage 1 seed complete ===")
    print(f"  Team:    {team['name']} (id={team['id']})")
    print(f"  Owner:   {owner_email} (uid={owner.id})")
    print(f"  Agent:   {agent_email} (uid={agent.id}, app_metadata.role=agent)")
    print()
    print("Next: run `python3 stage_1_verify.py` to confirm RLS policies work end-to-end.")


if __name__ == "__main__":
    main()
