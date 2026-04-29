import { useState, useEffect, useCallback } from "react";
import { api } from "../lib/api";

export interface OrgSummary {
  id: string;
  name: string;
  slug: string;
  owner_id: string;
  skill_convention: string;
  created_at: string;
}

export interface OrgMember {
  id: string;
  user_id: string;
  email: string | null;
  name: string | null;
  role: string;
}

export interface OrgTeam {
  id: string;
  name: string;
  skill_count: number;
}

export interface OrgDetail {
  id: string;
  name: string;
  slug: string;
  owner_id: string;
  skill_convention: string;
  created_at: string;
  teams: OrgTeam[];
  members: OrgMember[];
}

export interface OrgSkill {
  id: string;
  name: string;
  description: string | null;
  visibility: string;
  scope: string;
  team_id: string;
  team_name: string;
}

export interface UsageSummary {
  by_skill: { skill_name: string; count: number }[];
  by_team: { team_id: string; team_name: string; count: number }[];
}

export function useOrgs() {
  const [orgs, setOrgs] = useState<OrgSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setError(null);
      const data = await api.get<OrgSummary[]>("/api/v1/orgs");
      setOrgs(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load orgs");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const getOrg = useCallback(async (id: string): Promise<OrgDetail> => {
    return api.get<OrgDetail>(`/api/v1/orgs/${id}`);
  }, []);

  const createOrg = useCallback(
    async (name: string, slug: string) => {
      const result = await api.post<OrgSummary>("/api/v1/orgs", { name, slug });
      await refresh();
      return result;
    },
    [refresh],
  );

  const updateOrg = useCallback(
    async (id: string, updates: { name?: string; slug?: string; skill_convention?: string }) => {
      await api.put(`/api/v1/orgs/${id}`, updates);
      await refresh();
    },
    [refresh],
  );

  const deleteOrg = useCallback(
    async (id: string) => {
      await api.delete(`/api/v1/orgs/${id}`);
      await refresh();
    },
    [refresh],
  );

  const getOrgSkills = useCallback(async (id: string) => {
    const data = await api.get<{ skills: OrgSkill[] }>(`/api/v1/orgs/${id}/skills`);
    return data.skills;
  }, []);

  const getUsageSummary = useCallback(async (id: string) => {
    return api.get<UsageSummary>(`/api/v1/orgs/${id}/usage/summary`);
  }, []);

  const addMember = useCallback(async (orgId: string, email: string) => {
    return api.post<OrgMember>(`/api/v1/orgs/${orgId}/members`, { email });
  }, []);

  const removeMember = useCallback(async (orgId: string, memberId: string) => {
    await api.delete(`/api/v1/orgs/${orgId}/members/${memberId}`);
  }, []);

  const linkTeam = useCallback(async (orgId: string, teamId: string) => {
    await api.post(`/api/v1/orgs/${orgId}/teams/${teamId}`, {});
  }, []);

  const unlinkTeam = useCallback(async (orgId: string, teamId: string) => {
    await api.delete(`/api/v1/orgs/${orgId}/teams/${teamId}`);
  }, []);

  return {
    orgs, loading, error, refresh,
    getOrg, createOrg, updateOrg, deleteOrg,
    getOrgSkills, getUsageSummary,
    addMember, removeMember, linkTeam, unlinkTeam,
  };
}
