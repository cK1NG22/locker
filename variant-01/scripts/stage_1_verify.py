#!/usr/bin/env python3
"""Stage 1 verify — Stop+review gate for Stage 1.

Five RLS tests (per Subagent 1's research, baked into the build plan):
    1. Owner can SELECT teams via membership                     (positive)
    2. Agent can SELECT teams via membership                     (positive)
    3. Owner can UPDATE teams (owner + not agent)                (positive)
    4. Agent UPDATE teams silently filters (no error, 0 rows)    (negative — silent)
    5. Agent INSERT memberships raises 42501                     (negative — error)

Tests 4 and 5 use different patterns because Postgres handles RLS violations
differently for different operations:
    - INSERT violations throw error 42501 (insufficient_privilege).
    - UPDATE/DELETE/SELECT violations silently filter rows out (no error).
Both must be tested. A "passes" verify means the policies are working; a
"fails" means the schema is letting agents do something they shouldn't.

Usage:
    cd ~/Projects/locker/variant-01/scripts
    python3 stage_1_verify.py
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    from supabase import Client, create_client
    from postgrest.exceptions import APIError
except ImportError:
    print("Missing dependency: supabase. Install with `pip install supabase`.", file=sys.stderr)
    sys.exit(1)


def load_env() -> dict[str, str]:
    env_path = Path(__file__).parent / ".env"
    env: dict[str, str] = {}
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def sign_in(url: str, anon_key: str, email: str, password: str) -> Client:
    client = create_client(url, anon_key)
    client.auth.sign_in_with_password({"email": email, "password": password})
    return client


def report(label: str, ok: bool, detail: str = "") -> bool:
    mark = "PASS" if ok else "FAIL"
    suffix = f"  ({detail})" if detail else ""
    print(f"  [{mark}] {label}{suffix}")
    return ok


def main() -> None:
    env = load_env()
    url = env["SUPABASE_URL"]
    anon = env["SUPABASE_ANON_KEY"]

    print("Stage 1 verify — RLS policy end-to-end check\n")

    print("Signing in as owner (Carter)...")
    owner_client = sign_in(url, anon, env["OPTIMAL_OWNER_EMAIL"], env["OPTIMAL_OWNER_PASSWORD"])
    print("Signing in as agent (cos-sync-agent)...\n")
    agent_client = sign_in(url, anon, env["COS_AGENT_EMAIL"], env["COS_AGENT_PASSWORD"])

    results: list[bool] = []

    # --- Test 1: Owner SELECT teams ---
    teams = owner_client.table("teams").select("*").execute()
    results.append(
        report(
            "Test 1 — Owner can SELECT teams via membership",
            len(teams.data) == 1,
            f"rows={len(teams.data)}",
        )
    )

    # --- Test 2: Agent SELECT teams ---
    teams = agent_client.table("teams").select("*").execute()
    results.append(
        report(
            "Test 2 — Agent can SELECT teams via membership",
            len(teams.data) == 1,
            f"rows={len(teams.data)}",
        )
    )

    # --- Test 3: Owner UPDATE teams (no-op rename) ---
    team_id = owner_client.table("teams").select("id").execute().data[0]["id"]
    upd = (
        owner_client.table("teams")
        .update({"name": env["OPTIMAL_TEAM_NAME"]})
        .eq("id", team_id)
        .execute()
    )
    results.append(
        report(
            "Test 3 — Owner can UPDATE teams (owner + not agent)",
            len(upd.data) == 1,
            f"affected={len(upd.data)}",
        )
    )

    # --- Test 4: Agent UPDATE teams silently filters (no error, zero rows) ---
    upd = (
        agent_client.table("teams")
        .update({"name": "AGENT_HACK_ATTEMPT"})
        .eq("id", team_id)
        .execute()
    )
    results.append(
        report(
            "Test 4 — Agent UPDATE teams silently filters (no rows affected)",
            len(upd.data) == 0,
            f"affected={len(upd.data)}",
        )
    )

    # --- Test 5: Agent INSERT memberships raises 42501 ---
    raised = False
    raised_detail = ""
    try:
        agent_client.table("memberships").insert(
            {
                "user_id": "00000000-0000-0000-0000-000000000000",
                "team_id": team_id,
                "role": "owner",
            }
        ).execute()
    except APIError as e:
        raised = True
        raised_detail = f"code={getattr(e, 'code', '?')}"
    results.append(
        report(
            "Test 5 — Agent INSERT memberships raises (RLS reject)",
            raised,
            raised_detail or "no exception raised",
        )
    )

    # --- Summary ---
    print()
    passed = sum(1 for r in results if r)
    total = len(results)
    print(f"=== {passed}/{total} tests passed ===")
    if passed == total:
        print("\nStage 1 stop+review gate: GREEN. You can proceed to Stage 2.")
        sys.exit(0)
    else:
        print("\nStage 1 stop+review gate: RED. Fix before proceeding.")
        sys.exit(1)


if __name__ == "__main__":
    main()
