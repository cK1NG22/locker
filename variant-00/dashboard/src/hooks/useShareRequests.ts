import { useState, useCallback } from "react";
import { api } from "../lib/api";

export interface ShareRequest {
  id: string;
  skill_id: string;
  skill_name: string;
  from_team_id: string;
  from_team_name: string;
  to_team_id: string;
  to_team_name: string;
  requested_by: string;
  status: string;
  created_at: string;
  resolved_at: string | null;
}

export function useShareRequests() {
  const [requests, setRequests] = useState<ShareRequest[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchRequests = useCallback(async (teamId?: string) => {
    setLoading(true);
    try {
      const url = teamId
        ? `/api/v1/share-requests?team_id=${teamId}`
        : "/api/v1/share-requests";
      const data = await api.get<{ requests: ShareRequest[] }>(url);
      setRequests(data.requests);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, []);

  const createRequest = useCallback(
    async (skillId: string, fromTeamId: string, toTeamId: string) => {
      return api.post("/api/v1/share-requests", {
        skill_id: skillId,
        from_team_id: fromTeamId,
        to_team_id: toTeamId,
      });
    },
    [],
  );

  const resolveRequest = useCallback(
    async (requestId: string, status: "approved" | "denied") => {
      return api.patch(`/api/v1/share-requests/${requestId}`, { status });
    },
    [],
  );

  return { requests, loading, error, fetchRequests, createRequest, resolveRequest };
}
