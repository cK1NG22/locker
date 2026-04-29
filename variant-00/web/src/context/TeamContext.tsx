"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useRef,
  type ReactNode,
} from "react";
import { usePathname } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import { STORAGE_KEYS } from "@/lib/constants";

interface MyTeam {
  team_id: string;
  team_name: string;
  slug: string | null;
  role: string;
  can_share: boolean;
  skill_count: number;
}

interface TeamContextValue {
  teams: MyTeam[];
  activeTeam: MyTeam | null;
  activeRole: string | null;
  setActiveTeam: (teamId: string) => void;
  loading: boolean;
  refresh: () => Promise<void>;
}

const TeamContext = createContext<TeamContextValue | null>(null);

export function TeamProvider({ children }: { children: ReactNode }) {
  const { token } = useAuth();
  const pathname = usePathname();
  const [teams, setTeams] = useState<MyTeam[]>([]);
  const [activeTeamId, setActiveTeamId] = useState<string | null>(() => {
    if (typeof window === "undefined") return null;
    // Check URL param first (from invite flow)
    const params = new URLSearchParams(window.location.search);
    const urlTeam = params.get("team");
    if (urlTeam) {
      localStorage.setItem(STORAGE_KEYS.ACTIVE_TEAM, urlTeam);
      return urlTeam;
    }
    return localStorage.getItem(STORAGE_KEYS.ACTIVE_TEAM);
  });
  const [loading, setLoading] = useState(true);
  const [needsFetch, setNeedsFetch] = useState(0);
  const fetchCountRef = useRef(0);

  // Pick up ?team= param on navigation (e.g. after invite join → dashboard)
  // If the team isn't in the current list, re-fetch
  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    const urlTeam = params.get("team");
    if (urlTeam) {
      if (urlTeam !== activeTeamId) {
        setActiveTeamId(urlTeam);
        localStorage.setItem(STORAGE_KEYS.ACTIVE_TEAM, urlTeam);
      }
      // If team not in current list, we need to re-fetch
      if (!teams.find((t) => t.team_id === urlTeam)) {
        // Trigger re-fetch by incrementing counter
        setNeedsFetch((n) => n + 1);
      }
    }
  }, [pathname]); // eslint-disable-line react-hooks/exhaustive-deps

  const refresh = useCallback(async () => {
    if (!token) {
      setTeams([]);
      setLoading(false);
      return;
    }
    const fetchId = ++fetchCountRef.current;
    try {
      const data = await api.get<MyTeam[]>("/api/v1/me/teams");
      // Stale response guard
      if (fetchId !== fetchCountRef.current) return;
      setTeams(data);
      setActiveTeamId((prev) => {
        // Auto-select if only 1 team and no active selection
        if (data.length === 1 && !prev) {
          localStorage.setItem(STORAGE_KEYS.ACTIVE_TEAM, data[0].team_id);
          return data[0].team_id;
        }
        // Validate stored active team still exists
        if (prev && !data.find((t) => t.team_id === prev)) {
          const fallback = data.length > 0 ? data[0].team_id : null;
          if (fallback) {
            localStorage.setItem(STORAGE_KEYS.ACTIVE_TEAM, fallback);
          } else {
            localStorage.removeItem(STORAGE_KEYS.ACTIVE_TEAM);
          }
          return fallback;
        }
        return prev;
      });
    } catch {
      if (fetchId !== fetchCountRef.current) return;
      setTeams([]);
    } finally {
      if (fetchId === fetchCountRef.current) setLoading(false);
    }
  }, [token]);

  // Fetch on token change or when a re-fetch is needed (e.g. post-join)
  useEffect(() => {
    refresh();
  }, [refresh, needsFetch]);

  const setActiveTeam = useCallback((teamId: string) => {
    setActiveTeamId(teamId);
    localStorage.setItem(STORAGE_KEYS.ACTIVE_TEAM, teamId);
  }, []);

  const activeTeam = teams.find((t) => t.team_id === activeTeamId) ?? null;
  const activeRole = activeTeam?.role ?? null;

  return (
    <TeamContext.Provider
      value={{ teams, activeTeam, activeRole, setActiveTeam, loading, refresh }}
    >
      {children}
    </TeamContext.Provider>
  );
}

export function useTeamContext(): TeamContextValue {
  const ctx = useContext(TeamContext);
  if (!ctx) throw new Error("useTeamContext must be used within TeamProvider");
  return ctx;
}
