"use client";

import { useState, useEffect } from "react";
import { useTeamContext } from "@/context/TeamContext";
import { api } from "@/lib/api";

interface TeamMember {
  id: string;
  user_id: string;
  email: string | null;
  name: string | null;
  role: string;
  can_share: boolean;
  created_at: string;
}

interface TeamDetailData {
  id: string;
  name: string;
  slug: string | null;
  members: TeamMember[];
  skills: string[];
}

export default function TeamPage() {
  const { activeTeam, loading: teamLoading } = useTeamContext();
  const [team, setTeam] = useState<TeamDetailData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (teamLoading || !activeTeam) return;
    setLoading(true);
    api
      .get<TeamDetailData>(`/api/v1/teams/${activeTeam.team_id}`)
      .then(setTeam)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load team"))
      .finally(() => setLoading(false));
  }, [activeTeam, teamLoading]);

  if (teamLoading || loading) {
    return <p className="text-sm text-gray-500">Loading team...</p>;
  }
  if (error) return <p className="text-sm text-red-600">{error}</p>;
  if (!team) return null;

  return (
    <div>
      <h2 className="text-lg font-semibold text-gray-900 mb-1">{team.name}</h2>
      <p className="text-xs text-gray-400 mb-6">
        {team.members.length} member{team.members.length !== 1 ? "s" : ""} &middot;{" "}
        {team.skills.length} skill{team.skills.length !== 1 ? "s" : ""}
      </p>

      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 bg-gray-50">
              <th className="text-left px-4 py-3 font-medium text-gray-600">Name</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Email</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Role</th>
            </tr>
          </thead>
          <tbody>
            {team.members.map((m) => (
              <tr key={m.id} className="border-b border-gray-100 last:border-0">
                <td className="px-4 py-3 text-gray-900">{m.name || "--"}</td>
                <td className="px-4 py-3 text-gray-500">{m.email || "--"}</td>
                <td className="px-4 py-3">
                  <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${m.role === "admin" ? "bg-blue-100 text-blue-700" : "bg-gray-100 text-gray-600"}`}>
                    {m.role}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
