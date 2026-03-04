import { useState, useEffect, useCallback } from "react";

export interface Skill {
  name: string;
  description: string | null;
}

interface SkillsResponse {
  team: string;
  skills: Skill[];
}

interface UseSkillsResult {
  team: string | null;
  skills: Skill[];
  loading: boolean;
  error: string | null;
}

const REFRESH_INTERVAL = 30_000;

export function useSkills(token: string | null): UseSkillsResult {
  const [team, setTeam] = useState<string | null>(null);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchSkills = useCallback(async () => {
    if (!token) return;

    try {
      const res = await fetch("/api/v1/employee/skills", {
        headers: { "X-Team-Token": token },
      });

      if (!res.ok) {
        if (res.status === 401) {
          setError("Invalid team token");
        } else {
          setError(`Server error (${res.status})`);
        }
        setSkills([]);
        setTeam(null);
        return;
      }

      const data: SkillsResponse = await res.json();
      setTeam(data.team);
      setSkills(data.skills);
      setError(null);
    } catch {
      setError("Cannot reach server");
    }
  }, [token]);

  // Initial load
  useEffect(() => {
    if (!token) return;
    setLoading(true);
    fetchSkills().finally(() => setLoading(false));
  }, [token, fetchSkills]);

  // Auto-refresh every 30 seconds
  useEffect(() => {
    if (!token || error) return;
    const id = setInterval(fetchSkills, REFRESH_INTERVAL);
    return () => clearInterval(id);
  }, [token, error, fetchSkills]);

  return { team, skills, loading, error };
}
