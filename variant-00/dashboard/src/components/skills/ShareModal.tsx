import { useState } from "react";
import type { TeamSummary } from "../../hooks/useTeams";

interface ShareModalProps {
  skillId: string;
  teams: TeamSummary[];
  copyToTeam: (skillId: string, teamId: string) => Promise<{ id: string }>;
}

export default function ShareModal({ skillId, teams, copyToTeam }: ShareModalProps) {
  const [showModal, setShowModal] = useState(false);
  const [shareTeamId, setShareTeamId] = useState("");
  const [sharing, setSharing] = useState(false);
  const [shareError, setShareError] = useState<string | null>(null);
  const [shareSuccess, setShareSuccess] = useState<string | null>(null);

  const handleShare = async () => {
    if (!shareTeamId) return;
    setSharing(true);
    setShareError(null);
    setShareSuccess(null);
    try {
      const result = await copyToTeam(skillId, shareTeamId);
      setShareSuccess(`Copied as new skill (ID: ${result.id})`);
      setShareTeamId("");
    } catch (e) {
      setShareError(e instanceof Error ? e.message : "Copy failed");
    } finally {
      setSharing(false);
    }
  };

  return (
    <div className="mb-6">
      <button
        type="button"
        onClick={() => { setShowModal(true); setShareError(null); setShareSuccess(null); }}
        className="text-sm text-blue-600 hover:text-blue-800 transition-colors"
      >
        Share to team...
      </button>

      {showModal && (
        <div className="mt-3 border border-gray-200 rounded-lg p-4 bg-gray-50 space-y-3">
          <p className="text-sm font-medium text-gray-700">Copy this skill to another team</p>
          <select
            value={shareTeamId}
            onChange={(e) => setShareTeamId(e.target.value)}
            className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Select a team...</option>
            {teams.map((t) => (
              <option key={t.id} value={t.id}>{t.name}</option>
            ))}
          </select>
          {shareError && <p className="text-sm text-red-600">{shareError}</p>}
          {shareSuccess && <p className="text-sm text-green-600">{shareSuccess}</p>}
          <div className="flex gap-2">
            <button
              type="button"
              onClick={handleShare}
              disabled={!shareTeamId || sharing}
              className="px-3 py-1.5 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {sharing ? "Copying..." : "Copy to team"}
            </button>
            <button
              type="button"
              onClick={() => { setShowModal(false); setShareTeamId(""); setShareError(null); setShareSuccess(null); }}
              className="px-3 py-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
