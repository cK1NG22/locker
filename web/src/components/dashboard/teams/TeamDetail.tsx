"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { useTeams, type TeamDetail as TeamDetailType, type TeamMember, type TeamCreated } from "@/hooks/useTeams";
import { useSkills, type SkillMeta } from "@/hooks/useSkills";
import { copyToClipboard } from "@/lib/clipboard";

export default function TeamDetail() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const router = useRouter();
  const { getTeam, updateTeam, deleteTeam, setTeamSkills, updateMember, addMember, removeMember, rotateToken } = useTeams();
  const { skills: allSkills } = useSkills();

  const [team, setTeam] = useState<TeamDetailType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showTokenModal, setShowTokenModal] = useState<TeamCreated | null>(null);
  const [tokenCopied, setTokenCopied] = useState(false);
  const [linkCopied, setLinkCopied] = useState(false);
  const [inviteLinkCopied, setInviteLinkCopied] = useState(false);
  const [rotating, setRotating] = useState(false);
  const [editingName, setEditingName] = useState(false);
  const [nameValue, setNameValue] = useState("");
  const [saving, setSaving] = useState(false);
  const [assignedSkillIds, setAssignedSkillIds] = useState<Set<string>>(new Set());
  const [savingSkills, setSavingSkills] = useState(false);
  const [newMemberEmail, setNewMemberEmail] = useState("");
  const [addingMember, setAddingMember] = useState(false);
  const [memberError, setMemberError] = useState<string | null>(null);

  const loadTeam = useCallback(async () => {
    if (!id) return;
    try {
      const t = await getTeam(id);
      setTeam(t);
      setNameValue(t.name);
      const ids = new Set(allSkills.filter((s: SkillMeta) => t.skills.includes(s.name)).map((s: SkillMeta) => s.id));
      setAssignedSkillIds(ids);
    } catch (e) { setError(e instanceof Error ? e.message : "Failed to load team"); }
    finally { setLoading(false); }
  }, [id, getTeam, allSkills]);

  useEffect(() => { loadTeam(); }, [loadTeam]);

  const handleRotateToken = async () => {
    if (!id || !confirm("Rotate this team's token? The old token will stop working immediately.")) return;
    setRotating(true);
    try { const result = await rotateToken(id); setShowTokenModal(result); await loadTeam(); }
    catch (e) { alert(e instanceof Error ? e.message : "Rotate failed"); }
    finally { setRotating(false); }
  };

  const saveName = async () => {
    if (!id || !nameValue.trim() || nameValue === team?.name) { setEditingName(false); return; }
    setSaving(true);
    try { await updateTeam(id, nameValue.trim()); setTeam((t) => t ? { ...t, name: nameValue.trim() } : t); setEditingName(false); }
    catch (e) { alert(e instanceof Error ? e.message : "Save failed"); }
    finally { setSaving(false); }
  };

  const toggleSkill = (skillId: string) => {
    setAssignedSkillIds((prev) => { const next = new Set(prev); if (next.has(skillId)) next.delete(skillId); else next.add(skillId); return next; });
  };

  const saveSkillAssignments = async () => {
    if (!id) return;
    setSavingSkills(true);
    try { await setTeamSkills(id, Array.from(assignedSkillIds)); await loadTeam(); }
    catch (e) { alert(e instanceof Error ? e.message : "Save failed"); }
    finally { setSavingSkills(false); }
  };

  const handleDelete = async () => {
    if (!id || !confirm(`Delete team "${team?.name}"?`)) return;
    try { await deleteTeam(id); router.push("/dashboard/teams"); }
    catch (e) { alert(e instanceof Error ? e.message : "Delete failed"); }
  };

  const handleAddMember = async () => {
    if (!id || !newMemberEmail.trim()) return;
    setAddingMember(true); setMemberError(null);
    try { await addMember(id, newMemberEmail.trim()); setNewMemberEmail(""); await loadTeam(); }
    catch (e) { setMemberError(e instanceof Error ? e.message : "Failed to add member"); }
    finally { setAddingMember(false); }
  };

  const handleRemoveMember = async (member: TeamMember) => {
    if (!id || !confirm(`Remove ${member.email || member.user_id} from this team?`)) return;
    try { await removeMember(id, member.id); await loadTeam(); }
    catch (e) { alert(e instanceof Error ? e.message : "Remove failed"); }
  };

  const handleUpdateMember = async (memberId: string, updates: { role?: string; can_share?: boolean }) => {
    if (!id) return;
    try { await updateMember(id, memberId, updates); await loadTeam(); }
    catch (e) { alert(e instanceof Error ? e.message : "Update failed"); }
  };

  if (loading) return <p className="text-sm text-gray-500">Loading...</p>;
  if (error) return <p className="text-sm text-red-600">{error}</p>;
  if (!team) return null;

  const inviteLink = team.slug ? `${typeof window !== "undefined" ? window.location.origin : ""}/join/${team.slug}` : null;

  return (
    <div className="max-w-xl">
      <button onClick={() => router.push("/dashboard/teams")} className="text-sm text-gray-500 hover:text-gray-700 mb-4 transition-colors">&larr; Back to teams</button>

      {/* Name */}
      <div className="mb-4">
        {editingName ? (
          <div className="flex items-center gap-2">
            <input value={nameValue} onChange={(e) => setNameValue(e.target.value)} className="text-lg font-semibold text-gray-900 border border-gray-300 rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500" autoFocus onKeyDown={(e) => { if (e.key === "Enter") saveName(); if (e.key === "Escape") { setEditingName(false); setNameValue(team.name); } }} />
            <button onClick={saveName} disabled={saving} className="text-sm text-blue-600 hover:underline">Save</button>
            <button onClick={() => { setEditingName(false); setNameValue(team.name); }} className="text-sm text-gray-400 hover:underline">Cancel</button>
          </div>
        ) : (
          <h2 className="text-lg font-semibold text-gray-900 cursor-pointer hover:text-blue-600 transition-colors" onClick={() => setEditingName(true)} title="Click to rename">{team.name}</h2>
        )}
      </div>

      {/* Invite Link */}
      {inviteLink && (
        <div className="mb-6">
          <label className="text-xs text-gray-400 uppercase tracking-wide">Invite Link</label>
          <div className="mt-1 flex items-center gap-2">
            <code className="flex-1 bg-gray-100 px-3 py-2 rounded text-sm font-mono text-gray-700 select-all truncate">{inviteLink}</code>
            <button onClick={() => copyToClipboard(inviteLink, setInviteLinkCopied)} className="px-3 py-2 text-sm border border-gray-200 rounded-md hover:bg-gray-50 transition-colors whitespace-nowrap">
              {inviteLinkCopied ? "Copied!" : "Copy Link"}
            </button>
          </div>
        </div>
      )}

      {/* Token */}
      <div className="mb-6">
        <label className="text-xs text-gray-400 uppercase tracking-wide">Team Token</label>
        <div className="mt-1 flex items-center gap-2">
          <code className="flex-1 bg-gray-100 px-3 py-2 rounded text-sm font-mono text-gray-700">{team.token_prefix}...</code>
          <button onClick={handleRotateToken} disabled={rotating} className="px-3 py-2 text-sm border border-gray-200 rounded-md hover:bg-gray-50 transition-colors whitespace-nowrap">{rotating ? "Rotating..." : "Rotate Token"}</button>
        </div>
        <p className="text-xs text-gray-400 mt-1">The full token is only shown once when created or rotated.</p>
      </div>

      {/* Token modal */}
      {showTokenModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-1">New Team Token</h3>
            <p className="text-sm text-red-600 mb-4">Save this token now — it won&apos;t be shown again.</p>
            <label className="text-xs text-gray-400 uppercase tracking-wide">Token</label>
            <div className="mt-1 mb-4 flex items-center gap-2">
              <code className="flex-1 bg-gray-100 px-3 py-2 rounded text-sm font-mono text-gray-700 select-all break-all">{showTokenModal.token}</code>
              <button onClick={() => copyToClipboard(showTokenModal.token, setTokenCopied)} className="px-3 py-2 text-sm border border-gray-200 rounded-md hover:bg-gray-50 transition-colors whitespace-nowrap">{tokenCopied ? "Copied!" : "Copy"}</button>
            </div>
            <label className="text-xs text-gray-400 uppercase tracking-wide">Invite Link</label>
            <div className="mt-1 mb-4 flex items-center gap-2">
              <code className="flex-1 bg-gray-100 px-3 py-2 rounded text-sm font-mono text-gray-700 select-all truncate">{showTokenModal.slug ? `${window.location.origin}/join/${showTokenModal.slug}` : "No slug available"}</code>
              <button onClick={() => { if (showTokenModal.slug) copyToClipboard(`${window.location.origin}/join/${showTokenModal.slug}`, setLinkCopied); }} className="px-3 py-2 text-sm border border-gray-200 rounded-md hover:bg-gray-50 transition-colors whitespace-nowrap">{linkCopied ? "Copied!" : "Copy Link"}</button>
            </div>
            <button onClick={() => { setShowTokenModal(null); setTokenCopied(false); setLinkCopied(false); setInviteLinkCopied(false); }} className="w-full px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 transition-colors">Done</button>
          </div>
        </div>
      )}

      {/* Skill assignment */}
      <div className="mb-6">
        <label className="text-xs text-gray-400 uppercase tracking-wide">Assigned Skills</label>
        {allSkills.length === 0 ? (
          <p className="mt-2 text-sm text-gray-500">No skills available. Upload skills first.</p>
        ) : (
          <div className="mt-2 space-y-1">
            {allSkills.map((skill: SkillMeta) => (
              <label key={skill.id} className="flex items-center gap-2 px-3 py-2 rounded hover:bg-gray-50 cursor-pointer">
                <input type="checkbox" checked={assignedSkillIds.has(skill.id)} onChange={() => toggleSkill(skill.id)} disabled={savingSkills} className="rounded border-gray-300 text-blue-600 focus:ring-blue-500" />
                <span className="text-sm font-mono text-gray-700">{skill.name}</span>
                {skill.description && <span className="text-xs text-gray-400 truncate">{skill.description}</span>}
              </label>
            ))}
            <button onClick={saveSkillAssignments} disabled={savingSkills} className="mt-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 disabled:opacity-50 transition-colors">{savingSkills ? "Saving..." : "Save assignments"}</button>
          </div>
        )}
      </div>

      {/* Members */}
      <div className="mb-6">
        <label className="text-xs text-gray-400 uppercase tracking-wide">Members</label>
        <div className="mt-2 flex items-center gap-2">
          <input type="email" placeholder="Email address" value={newMemberEmail} onChange={(e) => setNewMemberEmail(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") handleAddMember(); }} className="flex-1 border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
          <button onClick={handleAddMember} disabled={addingMember || !newMemberEmail.trim()} className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 disabled:opacity-50 transition-colors">{addingMember ? "Adding..." : "Add"}</button>
        </div>
        {memberError && <p className="text-xs text-red-600 mt-1">{memberError}</p>}
        <div className="mt-3 space-y-1">
          {(!team.members || team.members.length === 0) ? (
            <p className="text-sm text-gray-500">No members yet.</p>
          ) : (
            team.members.map((member: TeamMember) => (
              <div key={member.id} className="flex items-center gap-3 px-3 py-2 rounded hover:bg-gray-50">
                <div className="flex-1 min-w-0">
                  <span className="text-sm text-gray-700 truncate block">{member.email || member.user_id}</span>
                  {member.name && <span className="text-xs text-gray-400">{member.name}</span>}
                </div>
                <select value={member.role} onChange={(e) => handleUpdateMember(member.id, { role: e.target.value })} className="text-xs border border-gray-300 rounded px-2 py-1 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500">
                  <option value="member">Member</option>
                  <option value="admin">Admin</option>
                </select>
                <label className="flex items-center gap-1 text-xs text-gray-500 cursor-pointer">
                  <input type="checkbox" checked={member.can_share} onChange={(e) => handleUpdateMember(member.id, { can_share: e.target.checked })} className="rounded border-gray-300 text-blue-600 focus:ring-blue-500" />
                  Share
                </label>
                <button onClick={() => handleRemoveMember(member)} className="text-xs text-red-500 hover:text-red-700 transition-colors">Remove</button>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Metadata + delete */}
      <div className="flex items-center justify-between text-xs text-gray-400 pt-4 border-t border-gray-200">
        <span>Created {new Date(team.created_at).toLocaleString()}</span>
        <button onClick={handleDelete} className="text-red-500 hover:text-red-700 transition-colors">Delete team</button>
      </div>
    </div>
  );
}
