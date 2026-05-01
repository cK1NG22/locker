-- 0001_schema.sql — Stage 1: tenancy + auth principals + memberships + base RLS
--
-- Per ADRs ../docs/decisions/0001/0002/0003 + plan at ~/.claude/plans/dreamy-syncing-supabase.md.
-- Run via: Supabase Dashboard → SQL Editor → New Query → paste → Run.
-- Idempotent? No — re-running will error on existing objects. For re-run, drop the schema first.

-- ============================================================
-- Tables
-- ============================================================

create table public.teams (
  id          uuid primary key default gen_random_uuid(),
  name        text not null,
  slug        text unique not null,
  created_at  timestamptz not null default now()
);

comment on table public.teams is
  'Top-level tenancy unit. One row per Optimal-style firm. Optimal AI = the seeded firm for this dogfood.';

create table public.memberships (
  user_id     uuid not null references auth.users(id) on delete cascade,
  team_id     uuid not null references public.teams(id) on delete cascade,
  role        text not null check (role in ('owner','member','agent')),
  created_at  timestamptz not null default now(),
  primary key (user_id, team_id)
);

create index memberships_team_idx on public.memberships(team_id);
create index memberships_user_idx on public.memberships(user_id);

comment on table public.memberships is
  'Maps auth.users to teams with a role. Note: app_metadata.role on the JWT is the principal-type claim (agent vs human); memberships.role is the team-relationship claim. Both checked separately in RLS.';

-- ============================================================
-- SECURITY DEFINER helpers — break RLS recursion on memberships
-- (Without these, "see teammates" policies on memberships would
-- recurse on the same table.)
-- ============================================================

create or replace function public.is_team_member(target_team_id uuid)
returns boolean
language sql
security definer
set search_path = public
stable
as $$
  select exists (
    select 1 from public.memberships
    where team_id = target_team_id
      and user_id = auth.uid()
  );
$$;

comment on function public.is_team_member(uuid) is
  'SECURITY DEFINER membership check — bypasses RLS internally to avoid recursion in policies on memberships itself.';

create or replace function public.is_team_owner(target_team_id uuid)
returns boolean
language sql
security definer
set search_path = public
stable
as $$
  select exists (
    select 1 from public.memberships
    where team_id = target_team_id
      and user_id = auth.uid()
      and role = 'owner'
  );
$$;

comment on function public.is_team_owner(uuid) is
  'SECURITY DEFINER owner-role check.';

create or replace function public.is_agent()
returns boolean
language sql
stable
as $$
  -- Reads app_metadata.role from the JWT. app_metadata is server-set by Supabase
  -- (only service_role can write it), so it is RLS-trustable.
  -- Distinct from auth.jwt() ->> 'role' which is the Postgres-role claim
  -- and must remain 'authenticated'.
  select coalesce(
    (auth.jwt() -> 'app_metadata' ->> 'role') = 'agent',
    false
  );
$$;

comment on function public.is_agent() is
  'Returns true if the JWT has app_metadata.role=agent. Server-set, RLS-trustable. Use in WITH CHECK clauses to block agent writes.';

-- ============================================================
-- RLS — enable
-- ============================================================

alter table public.teams enable row level security;
alter table public.memberships enable row level security;

-- ============================================================
-- RLS — teams
-- Read: any member (humans + agents) of the team
-- Update: owners only, AND not an agent
-- Insert/Delete: no policy → anon/authenticated cannot do these.
--   (Service-role bypasses RLS, so seed scripts using service_role still work.)
-- ============================================================

create policy team_read_via_membership on public.teams
  for select
  using (public.is_team_member(id));

create policy team_update_owners_only on public.teams
  for update
  using (public.is_team_owner(id) and not public.is_agent())
  with check (public.is_team_owner(id) and not public.is_agent());

-- ============================================================
-- RLS — memberships
-- Read own: any user can SELECT their own membership rows
-- Read teammates: members can see other members of teams they belong to
-- Write (insert/update/delete): owners only, AND not an agent
-- ============================================================

create policy membership_read_own on public.memberships
  for select
  using (user_id = auth.uid());

create policy membership_read_teammates on public.memberships
  for select
  using (public.is_team_member(team_id));

create policy membership_write_owners_only on public.memberships
  for all
  using (public.is_team_owner(team_id) and not public.is_agent())
  with check (public.is_team_owner(team_id) and not public.is_agent());

-- ============================================================
-- Done. Stage 1 schema in place.
-- Next: stage_1_seed.py creates the Optimal AI team + 2 memberships.
-- ============================================================
