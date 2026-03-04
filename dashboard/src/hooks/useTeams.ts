import { useState, useEffect, useCallback } from "react";
import { api } from "../lib/api";

export interface TeamSummary {
  id: string;
  name: string;
  skill_count: number;
}

export interface TeamDetail {
  id: string;
  name: string;
  token: string;
  created_at: string;
  skills: string[];
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
      const result = await api.post<{ id: string; token: string }>("/api/v1/teams", { name });
      await refresh();
      return result;
    },
    [refresh],
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

  return { teams, loading, error, refresh, getTeam, createTeam, updateTeam, deleteTeam, setTeamSkills };
}
