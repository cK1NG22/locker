"use client";

import Link from "next/link";
import { useState } from "react";
import { useSkills } from "@/hooks/useSkills";
import { useMemberSkills } from "@/hooks/useMemberSkills";
import { useTeamContext } from "@/context/TeamContext";

function FeedbackModal({
  skillName,
  onSubmit,
  onClose,
}: {
  skillName: string;
  onSubmit: (text: string) => Promise<void>;
  onClose: () => void;
}) {
  const [text, setText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = async () => {
    if (!text.trim()) return;
    setSubmitting(true);
    try {
      await onSubmit(text);
      setSubmitted(true);
    } catch {
      alert("Failed to submit feedback");
    } finally {
      setSubmitting(false);
    }
  };

  if (submitted) {
    return (
      <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg shadow-lg p-6 max-w-sm w-full mx-4">
          <p className="text-sm text-gray-700 mb-4">Feedback submitted. Thank you!</p>
          <button onClick={onClose} className="px-4 py-2 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700">
            Close
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-lg p-6 max-w-sm w-full mx-4">
        <h3 className="text-sm font-semibold text-gray-900 mb-2">
          Feedback for &ldquo;{skillName}&rdquo;
        </h3>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="What would you like to improve?"
          className="w-full border border-gray-200 rounded-md p-2 text-sm h-24 resize-none focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
        <div className="flex justify-end gap-2 mt-3">
          <button onClick={onClose} className="px-3 py-1.5 text-sm text-gray-500 hover:text-gray-700">
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={!text.trim() || submitting}
            className="px-4 py-1.5 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            {submitting ? "Sending..." : "Submit"}
          </button>
        </div>
      </div>
    </div>
  );
}

function AdminSkillList() {
  const { skills, loading, error, deleteSkill } = useSkills();

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Delete skill "${name}"?`)) return;
    try {
      await deleteSkill(id);
    } catch (e) {
      alert(e instanceof Error ? e.message : "Delete failed");
    }
  };

  if (loading) return <p className="text-sm text-gray-500">Loading skills...</p>;
  if (error) return <p className="text-sm text-red-600">{error}</p>;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-lg font-semibold text-gray-900">Skills</h2>
        <Link href="/dashboard/skills/upload" className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 transition-colors">
          Upload skill
        </Link>
      </div>
      {skills.length === 0 ? (
        <p className="text-sm text-gray-500 py-8 text-center">No skills yet. Upload one to get started.</p>
      ) : (
        <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50">
                <th className="text-left px-4 py-3 font-medium text-gray-600">Name</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Description</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Uploaded by</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Updated</th>
                <th className="w-20 px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {skills.map((skill) => (
                <tr key={skill.id} className="border-b border-gray-100 last:border-0 hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <Link href={`/dashboard/skills/${skill.id}`} className="font-mono text-blue-600 hover:underline">{skill.name}</Link>
                      {skill.scope === "personal" && (
                        <span className="text-xs px-1.5 py-0.5 bg-amber-100 text-amber-700 rounded font-medium">Personal</span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-gray-500 truncate max-w-xs">{skill.description || "--"}</td>
                  <td className="px-4 py-3 text-gray-400 text-xs">{skill.uploaded_by_name || "--"}</td>
                  <td className="px-4 py-3 text-gray-400">{new Date(skill.updated_at).toLocaleDateString()}</td>
                  <td className="px-4 py-3">
                    <button onClick={() => handleDelete(skill.id, skill.name)} className="text-red-500 hover:text-red-700 text-xs transition-colors">Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function MemberSkillList() {
  const { activeTeam } = useTeamContext();
  const { skills, loading, error, submitFeedback } = useMemberSkills(
    activeTeam?.team_id ?? null,
  );
  const [feedbackSkill, setFeedbackSkill] = useState<{
    id: string;
    name: string;
  } | null>(null);

  if (loading) return <p className="text-sm text-gray-500">Loading skills...</p>;
  if (error) return <p className="text-sm text-red-600">{error}</p>;

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-lg font-semibold text-gray-900">Skills</h2>
        {activeTeam && (
          <p className="text-xs text-gray-400 mt-0.5">
            {activeTeam.team_name} &middot; {skills.length} skill
            {skills.length !== 1 ? "s" : ""}
          </p>
        )}
      </div>
      {skills.length === 0 ? (
        <p className="text-sm text-gray-500 py-8 text-center">
          No skills available yet. Your team admin will add skills soon.
        </p>
      ) : (
        <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50">
                <th className="text-left px-4 py-3 font-medium text-gray-600">Name</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Description</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Visibility</th>
                <th className="w-32 px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {skills.map((skill) => (
                <tr key={skill.id} className="border-b border-gray-100 last:border-0 hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-gray-900">{skill.name}</td>
                  <td className="px-4 py-3 text-gray-500 truncate max-w-xs">{skill.description || "--"}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${skill.visibility === "open" ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-600"}`}>
                      {skill.visibility}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() =>
                        setFeedbackSkill({ id: skill.id, name: skill.name })
                      }
                      className="text-blue-600 hover:text-blue-800 text-xs transition-colors"
                    >
                      Feedback
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {feedbackSkill && (
        <FeedbackModal
          skillName={feedbackSkill.name}
          onSubmit={(text) => submitFeedback(feedbackSkill.id, text)}
          onClose={() => setFeedbackSkill(null)}
        />
      )}
    </div>
  );
}

export default function SkillList() {
  const { activeRole, loading, teams } = useTeamContext();

  if (loading) return <p className="text-sm text-gray-500">Loading...</p>;

  if (teams.length === 0) {
    return (
      <div className="py-12 text-center">
        <h2 className="text-lg font-semibold text-gray-900 mb-2">No teams yet</h2>
        <p className="text-sm text-gray-500">
          You&apos;re not a member of any team. Ask a team admin for an invite link, or create a new team.
        </p>
      </div>
    );
  }

  if (activeRole === "admin") return <AdminSkillList />;
  return <MemberSkillList />;
}
