"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { useOrgs, type OrgSkill, type UsageSummary } from "@/hooks/useOrgs";

export default function OrgAnalytics() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const router = useRouter();
  const { getOrgSkills, getUsageSummary } = useOrgs();
  const [skills, setSkills] = useState<OrgSkill[]>([]);
  const [usage, setUsage] = useState<UsageSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    Promise.all([getOrgSkills(id), getUsageSummary(id)])
      .then(([s, u]) => { setSkills(s); setUsage(u); })
      .catch((e) => setError(e instanceof Error ? e.message : "Load failed"))
      .finally(() => setLoading(false));
  }, [id, getOrgSkills, getUsageSummary]);

  if (loading) return <p className="text-sm text-gray-500">Loading analytics...</p>;
  if (error) return <p className="text-sm text-red-600">{error}</p>;

  return (
    <div className="max-w-2xl">
      <button onClick={() => router.push(`/dashboard/orgs/${id}`)} className="text-sm text-gray-500 hover:text-gray-700 mb-4 transition-colors">&larr; Back to org</button>
      <h2 className="text-lg font-semibold text-gray-900 mb-6">Organization Analytics</h2>
      <div className="mb-8">
        <h3 className="text-sm font-medium text-gray-700 mb-2">Skills across teams ({skills.length})</h3>
        {skills.length === 0 ? <p className="text-sm text-gray-500">No skills assigned to org teams yet.</p> : (
          <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead><tr className="border-b border-gray-200 bg-gray-50"><th className="text-left px-4 py-2 font-medium text-gray-600">Skill</th><th className="text-left px-4 py-2 font-medium text-gray-600">Team</th><th className="text-left px-4 py-2 font-medium text-gray-600">Visibility</th></tr></thead>
              <tbody>{skills.map((s, i) => (<tr key={`${s.id}-${s.team_id}-${i}`} className="border-b border-gray-100 last:border-0"><td className="px-4 py-2 font-mono">{s.name}</td><td className="px-4 py-2 text-gray-500">{s.team_name}</td><td className="px-4 py-2 text-gray-400">{s.visibility}</td></tr>))}</tbody>
            </table>
          </div>
        )}
      </div>
      {usage && (
        <>
          <div className="mb-8">
            <h3 className="text-sm font-medium text-gray-700 mb-2">Usage by skill</h3>
            {usage.by_skill.length === 0 ? <p className="text-sm text-gray-500">No usage data yet.</p> : (
              <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
                <table className="w-full text-sm">
                  <thead><tr className="border-b border-gray-200 bg-gray-50"><th className="text-left px-4 py-2 font-medium text-gray-600">Skill</th><th className="text-right px-4 py-2 font-medium text-gray-600">Invocations</th></tr></thead>
                  <tbody>{usage.by_skill.map((row) => (<tr key={row.skill_name} className="border-b border-gray-100 last:border-0"><td className="px-4 py-2 font-mono">{row.skill_name}</td><td className="px-4 py-2 text-right text-gray-700">{row.count}</td></tr>))}</tbody>
                </table>
              </div>
            )}
          </div>
          <div className="mb-8">
            <h3 className="text-sm font-medium text-gray-700 mb-2">Usage by team</h3>
            {usage.by_team.length === 0 ? <p className="text-sm text-gray-500">No usage data yet.</p> : (
              <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
                <table className="w-full text-sm">
                  <thead><tr className="border-b border-gray-200 bg-gray-50"><th className="text-left px-4 py-2 font-medium text-gray-600">Team</th><th className="text-right px-4 py-2 font-medium text-gray-600">Invocations</th></tr></thead>
                  <tbody>{usage.by_team.map((row) => (<tr key={row.team_id} className="border-b border-gray-100 last:border-0"><td className="px-4 py-2">{row.team_name}</td><td className="px-4 py-2 text-right text-gray-700">{row.count}</td></tr>))}</tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
