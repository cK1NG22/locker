"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useOrgs, type OrgDetail as OrgDetailType, type OrgMember } from "@/hooks/useOrgs";
import { useTeams, type TeamSummary } from "@/hooks/useTeams";

export default function OrgDetail() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const router = useRouter();
  const { getOrg, updateOrg, deleteOrg, addMember, removeMember, linkTeam, unlinkTeam } = useOrgs();
  const { teams: allTeams } = useTeams();
  const [org, setOrg] = useState<OrgDetailType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newMemberEmail, setNewMemberEmail] = useState("");
  const [addingMember, setAddingMember] = useState(false);
  const [memberError, setMemberError] = useState<string | null>(null);
  const [selectedTeamId, setSelectedTeamId] = useState("");
  const [linkingTeam, setLinkingTeam] = useState(false);
  const [editingConvention, setEditingConvention] = useState(false);
  const [conventionValue, setConventionValue] = useState("");
  const [savingConvention, setSavingConvention] = useState(false);

  const loadOrg = useCallback(async () => {
    if (!id) return;
    try { const o = await getOrg(id); setOrg(o); }
    catch (e) { setError(e instanceof Error ? e.message : "Failed to load org"); }
    finally { setLoading(false); }
  }, [id, getOrg]);

  useEffect(() => { loadOrg(); }, [loadOrg]);

  const handleDelete = async () => {
    if (!id || !confirm(`Delete org "${org?.name}"?`)) return;
    try { await deleteOrg(id); router.push("/dashboard/orgs"); }
    catch (e) { alert(e instanceof Error ? e.message : "Delete failed"); }
  };

  const handleAddMember = async () => {
    if (!id || !newMemberEmail.trim()) return;
    setAddingMember(true); setMemberError(null);
    try { await addMember(id, newMemberEmail.trim()); setNewMemberEmail(""); await loadOrg(); }
    catch (e) { setMemberError(e instanceof Error ? e.message : "Failed to add member"); }
    finally { setAddingMember(false); }
  };

  const handleRemoveMember = async (member: OrgMember) => {
    if (!id || !confirm(`Remove ${member.email || member.user_id}?`)) return;
    try { await removeMember(id, member.id); await loadOrg(); }
    catch (e) { alert(e instanceof Error ? e.message : "Remove failed"); }
  };

  const handleLinkTeam = async () => {
    if (!id || !selectedTeamId) return;
    setLinkingTeam(true);
    try { await linkTeam(id, selectedTeamId); setSelectedTeamId(""); await loadOrg(); }
    catch (e) { alert(e instanceof Error ? e.message : "Link failed"); }
    finally { setLinkingTeam(false); }
  };

  const handleUnlinkTeam = async (teamId: string, teamName: string) => {
    if (!id || !confirm(`Unlink team "${teamName}" from this org?`)) return;
    try { await unlinkTeam(id, teamId); await loadOrg(); }
    catch (e) { alert(e instanceof Error ? e.message : "Unlink failed"); }
  };

  if (loading) return <p className="text-sm text-gray-500">Loading...</p>;
  if (error) return <p className="text-sm text-red-600">{error}</p>;
  if (!org) return null;

  const linkedTeamIds = new Set(org.teams.map((t) => t.id));
  const unlinkedTeams = allTeams.filter((t: TeamSummary) => !linkedTeamIds.has(t.id));

  return (
    <div className="max-w-xl">
      <button onClick={() => router.push("/dashboard/orgs")} className="text-sm text-gray-500 hover:text-gray-700 mb-4 transition-colors">&larr; Back to orgs</button>
      <h2 className="text-lg font-semibold text-gray-900 mb-1">{org.name}</h2>
      <p className="text-sm text-gray-500 mb-6 font-mono">{org.slug}</p>
      <div className="mb-6">
        <label className="text-xs text-gray-400 uppercase tracking-wide">Teams</label>
        <div className="mt-2 space-y-1">
          {org.teams.map((team) => (
            <div key={team.id} className="flex items-center justify-between px-3 py-2 rounded hover:bg-gray-50">
              <span className="text-sm text-gray-700">{team.name} ({team.skill_count} skills)</span>
              <button onClick={() => handleUnlinkTeam(team.id, team.name)} className="text-xs text-red-500 hover:text-red-700">Unlink</button>
            </div>
          ))}
        </div>
        {unlinkedTeams.length > 0 && (
          <div className="mt-2 flex items-center gap-2">
            <select value={selectedTeamId} onChange={(e) => setSelectedTeamId(e.target.value)} className="flex-1 border border-gray-300 rounded px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500">
              <option value="">Select a team to link...</option>
              {unlinkedTeams.map((t: TeamSummary) => (<option key={t.id} value={t.id}>{t.name}</option>))}
            </select>
            <button onClick={handleLinkTeam} disabled={!selectedTeamId || linkingTeam} className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 disabled:opacity-50 transition-colors">Link</button>
          </div>
        )}
      </div>
      <div className="mb-6">
        <label className="text-xs text-gray-400 uppercase tracking-wide">Members</label>
        <div className="mt-2 flex items-center gap-2">
          <input type="email" placeholder="Email address" value={newMemberEmail} onChange={(e) => setNewMemberEmail(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") handleAddMember(); }} className="flex-1 border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
          <button onClick={handleAddMember} disabled={addingMember || !newMemberEmail.trim()} className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 disabled:opacity-50 transition-colors">{addingMember ? "Adding..." : "Add"}</button>
        </div>
        {memberError && <p className="text-xs text-red-600 mt-1">{memberError}</p>}
        <div className="mt-3 space-y-1">
          {org.members.map((member) => (
            <div key={member.id} className="flex items-center justify-between px-3 py-2 rounded hover:bg-gray-50">
              <div><span className="text-sm text-gray-700">{member.email || member.user_id}</span><span className="ml-2 text-xs text-gray-400">{member.role}</span></div>
              <button onClick={() => handleRemoveMember(member)} className="text-xs text-red-500 hover:text-red-700">Remove</button>
            </div>
          ))}
        </div>
      </div>
      <div className="mb-6"><Link href={`/dashboard/orgs/${org.id}/analytics`} className="text-sm text-blue-600 hover:underline">View usage analytics</Link></div>
      <div className="mb-6">
        <label className="text-xs text-gray-400 uppercase tracking-wide">Skill Convention</label>
        <p className="text-xs text-gray-400 mt-0.5 mb-2">The slash command prefix members use (e.g. /l, /locker)</p>
        {editingConvention ? (
          <div className="flex items-center gap-2 mt-1">
            <input
              type="text"
              value={conventionValue}
              onChange={(e) => setConventionValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  if (!id || !conventionValue.trim()) return;
                  setSavingConvention(true);
                  updateOrg(id, { skill_convention: conventionValue.trim() })
                    .then(() => { setEditingConvention(false); loadOrg(); })
                    .catch((err) => alert(err instanceof Error ? err.message : "Failed to update"))
                    .finally(() => setSavingConvention(false));
                }
                if (e.key === "Escape") setEditingConvention(false);
              }}
              className="border border-gray-300 rounded px-3 py-1.5 text-sm font-mono w-32 focus:outline-none focus:ring-2 focus:ring-blue-500"
              autoFocus
            />
            <button
              onClick={() => {
                if (!id || !conventionValue.trim()) return;
                setSavingConvention(true);
                updateOrg(id, { skill_convention: conventionValue.trim() })
                  .then(() => { setEditingConvention(false); loadOrg(); })
                  .catch((err) => alert(err instanceof Error ? err.message : "Failed to update"))
                  .finally(() => setSavingConvention(false));
              }}
              disabled={savingConvention || !conventionValue.trim()}
              className="px-3 py-1.5 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 disabled:opacity-50"
            >
              {savingConvention ? "Saving..." : "Save"}
            </button>
            <button onClick={() => setEditingConvention(false)} className="text-sm text-gray-500 hover:text-gray-700">Cancel</button>
          </div>
        ) : (
          <div className="flex items-center gap-2 mt-1">
            <code className="text-sm bg-gray-100 px-2 py-1 rounded">{org.skill_convention}</code>
            <button
              onClick={() => { setConventionValue(org.skill_convention); setEditingConvention(true); }}
              className="text-xs text-blue-600 hover:text-blue-800"
            >
              Change
            </button>
          </div>
        )}
      </div>
      <div className="flex items-center justify-between text-xs text-gray-400 pt-4 border-t border-gray-200">
        <span>Created {new Date(org.created_at).toLocaleString()}</span>
        <button onClick={handleDelete} className="text-red-500 hover:text-red-700 transition-colors">Delete org</button>
      </div>
    </div>
  );
}
