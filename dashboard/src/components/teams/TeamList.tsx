import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTeams, type TeamJoinResult } from "../../hooks/useTeams";
import { copyToClipboard } from "../../lib/clipboard";

export default function TeamList() {
  const navigate = useNavigate();
  const { teams, loading, error, deleteTeam, joinTeam } = useTeams();
  const [showJoinModal, setShowJoinModal] = useState(false);
  const [inviteCode, setInviteCode] = useState("");
  const [joining, setJoining] = useState(false);
  const [joinError, setJoinError] = useState<string | null>(null);
  const [joinResult, setJoinResult] = useState<TeamJoinResult | null>(null);
  const [patCopied, setPatCopied] = useState(false);

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Delete team "${name}"? Employees using this team's token will lose access.`)) return;
    try {
      await deleteTeam(id);
    } catch (e) {
      alert(e instanceof Error ? e.message : "Delete failed");
    }
  };

  const handleJoin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inviteCode.trim()) return;
    setJoining(true);
    setJoinError(null);
    try {
      const result = await joinTeam(inviteCode.trim());
      setJoinResult(result);
    } catch (e) {
      setJoinError(e instanceof Error ? e.message : "Join failed");
    } finally {
      setJoining(false);
    }
  };

  const closeJoinModal = () => {
    setShowJoinModal(false);
    setInviteCode("");
    setJoinError(null);
    if (joinResult && !joinResult.already_member) {
      setJoinResult(null);
      navigate(`/teams/${joinResult.team_id}`);
    } else {
      setJoinResult(null);
    }
  };

  if (loading) {
    return <p className="text-sm text-gray-500">Loading teams...</p>;
  }

  if (error) {
    return <p className="text-sm text-red-600">{error}</p>;
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-lg font-semibold text-gray-900">Teams</h2>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowJoinModal(true)}
            className="px-4 py-2 border border-gray-300 text-gray-700 text-sm font-medium rounded-md hover:bg-gray-50 transition-colors"
          >
            Join Team
          </button>
          <Link
            to="/teams/new"
            className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 transition-colors"
          >
            Create team
          </Link>
        </div>
      </div>

      {teams.length === 0 ? (
        <p className="text-sm text-gray-500 py-8 text-center">
          No teams yet. Create one or join with an invite code.
        </p>
      ) : (
        <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50">
                <th className="text-left px-4 py-3 font-medium text-gray-600">Name</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Skills</th>
                <th className="w-20 px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {teams.map((team) => (
                <tr key={team.id} className="border-b border-gray-100 last:border-0 hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <Link
                      to={`/teams/${team.id}`}
                      className="text-blue-600 hover:underline font-medium"
                    >
                      {team.name}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-gray-500">
                    {team.skill_count} skill{team.skill_count !== 1 ? "s" : ""}
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => handleDelete(team.id, team.name)}
                      className="text-red-500 hover:text-red-700 text-xs transition-colors"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Join Team Modal */}
      {showJoinModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
            {joinResult ? (
              // Post-join result
              <>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  {joinResult.already_member ? "Already a Member" : "Joined!"}
                </h3>
                {joinResult.already_member ? (
                  <p className="text-sm text-gray-600 mb-4">
                    You're already a member of <span className="font-medium">{joinResult.team_name}</span>.
                  </p>
                ) : (
                  <>
                    <p className="text-sm text-green-600 font-medium mb-4">
                      You've joined <span className="font-semibold">{joinResult.team_name}</span>!
                    </p>
                    {joinResult.personal_token && (
                      <div className="mb-4">
                        <p className="text-sm text-red-600 mb-2">Save your personal token now — it won't be shown again.</p>
                        <label className="text-xs text-gray-400 uppercase tracking-wide">MCP Setup</label>
                        <code className="block mt-1 bg-gray-100 px-3 py-2 rounded text-xs font-mono text-gray-700 select-all break-all whitespace-pre-wrap">
{`locker setup --token ${joinResult.personal_token}`}
                        </code>
                        <div className="mt-2 flex items-center gap-2">
                          <button
                            onClick={() => copyToClipboard(joinResult.personal_token!, setPatCopied)}
                            className="px-3 py-1 text-xs border border-gray-200 rounded hover:bg-gray-50 transition-colors"
                          >
                            {patCopied ? "Copied!" : "Copy Token"}
                          </button>
                        </div>
                      </div>
                    )}
                  </>
                )}
                <button
                  onClick={closeJoinModal}
                  className="w-full px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 transition-colors"
                >
                  {joinResult.already_member ? "Close" : "Go to Team"}
                </button>
              </>
            ) : (
              // Join form
              <>
                <h3 className="text-lg font-semibold text-gray-900 mb-1">Join a Team</h3>
                <p className="text-sm text-gray-500 mb-4">Enter the invite code shared by your team admin.</p>
                <form onSubmit={handleJoin}>
                  <input
                    type="text"
                    value={inviteCode}
                    onChange={(e) => setInviteCode(e.target.value.toUpperCase())}
                    placeholder="e.g. ACME-7X3K"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm font-mono tracking-wider text-center focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    autoFocus
                  />
                  {joinError && <p className="text-sm text-red-600 mt-2">{joinError}</p>}
                  <div className="flex gap-2 mt-4">
                    <button
                      type="button"
                      onClick={closeJoinModal}
                      className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 text-sm font-medium rounded-md hover:bg-gray-50 transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={!inviteCode.trim() || joining}
                      className="flex-1 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      {joining ? "Joining..." : "Join"}
                    </button>
                  </div>
                </form>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
