"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";

export interface MemberSkill {
  id: string;
  name: string;
  description: string | null;
  visibility: string;
  content: string | null;
}

export function useMemberSkills(teamId: string | null) {
  const [skills, setSkills] = useState<MemberSkill[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!teamId) {
      setSkills([]);
      setLoading(false);
      return;
    }
    try {
      setError(null);
      const data = await api.get<MemberSkill[]>(
        `/api/v1/teams/${teamId}/member-skills`,
      );
      setSkills(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load skills");
    } finally {
      setLoading(false);
    }
  }, [teamId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const submitFeedback = useCallback(
    async (skillId: string, feedbackText: string): Promise<void> => {
      if (!teamId) throw new Error("No active team");
      await api.post(`/api/v1/teams/${teamId}/skills/${skillId}/feedback`, {
        feedback_text: feedbackText,
      });
    },
    [teamId],
  );

  return { skills, loading, error, refresh, submitFeedback };
}
