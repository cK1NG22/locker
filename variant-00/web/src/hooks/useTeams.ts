"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";

export interface TeamSummary {
  id: string;
  name: string;
  slug?: string;
  skill_count: number;
}

export interface TeamMember {
  id: string;
  user_id: string;
  email: string | null;
  name: string | null;
  role: string;
  can_share: boolean;
  created_at: string;
}

export interface TeamDetail {
  id: string;
  name: string;
  slug?: string;
  token_prefix: string;
  owner_id: string | null;
  created_at: string;
  skills: string[];
  members: TeamMember[];
}

export interface TeamCreated {
  id: string;
  name: string;
  slug?: string;
  token: string;
  token_prefix: string;
  owner_id: string | null;
  created_at: string;
}

export function useTeams() {
  const [teams, setTeams] = useState<TeamSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setError(null);
      const data = await api.get<TeamSummary[]>("/api/v1/teams");
      setTeams(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load teams");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const getTeam = useCallback(async (id: string): Promise<TeamDetail> => {
    return api.get<TeamDetail>(`/api/v1/teams/${id}`);
  }, []);

  const createTeam = useCallback(
    async (name: string) => {
      const result = await api.post<TeamCreated>("/api/v1/teams", { name });
      await refresh();
      return result;
    },
    [refresh],
  );

  const rotateToken = useCallback(
    async (teamId: string) => {
      return api.post<TeamCreated>(`/api/v1/teams/${teamId}/rotate-token`, {});
    },
    [],
  );

  const updateTeam = useCallback(
    async (id: string, name: string) => {
      await api.put(`/api/v1/teams/${id}`, { name });
      await refresh();
    },
    [refresh],
  );

  const deleteTeam = useCallback(
    async (id: string) => {
      await api.delete(`/api/v1/teams/${id}`);
      await refresh();
    },
    [refresh],
  );

  const setTeamSkills = useCallback(
    async (teamId: string, skillIds: string[]) => {
      await api.put(`/api/v1/teams/${teamId}/skills`, { skill_ids: skillIds });
    },
    [],
  );

  const updateMember = useCallback(
    async (teamId: string, memberId: string, updates: { role?: string; can_share?: boolean }) => {
      await api.patch(`/api/v1/teams/${teamId}/members/${memberId}`, updates);
    },
    [],
  );

  const addMember = useCallback(
    async (teamId: string, email: string) => {
      return api.post<TeamMember>(`/api/v1/teams/${teamId}/members`, { email });
    },
    [],
  );

  const removeMember = useCallback(
    async (teamId: string, memberId: string) => {
      await api.delete(`/api/v1/teams/${teamId}/members/${memberId}`);
    },
    [],
  );

  return { teams, loading, error, refresh, getTeam, createTeam, rotateToken, updateTeam, deleteTeam, setTeamSkills, updateMember, addMember, removeMember };
}
