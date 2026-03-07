import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useShareRequests } from "../../hooks/useShareRequests";

export default function ShareRequests() {
  const { id: teamId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { requests, loading, error, fetchRequests, resolveRequest } = useShareRequests();
  const [resolving, setResolving] = useState<string | null>(null);

  useEffect(() => {
    if (teamId) fetchRequests(teamId);
  }, [teamId, fetchRequests]);

  const handleResolve = async (requestId: string, status: "approved" | "denied") => {
    setResolving(requestId);
    try {
      await resolveRequest(requestId, status);
      if (teamId) await fetchRequests(teamId);
    } catch (e) {
      alert(e instanceof Error ? e.message : "Failed");
    } finally {
      setResolving(null);
    }
  };

  if (loading) return <p className="text-sm text-gray-500">Loading share requests...</p>;
  if (error) return <p className="text-sm text-red-600">{error}</p>;

  return (
    <div className="max-w-xl">
      <button onClick={() => navigate(-1)} className="text-sm text-gray-500 hover:text-gray-700 mb-4 transition-colors">
        &larr; Back
      </button>

      <h2 className="text-lg font-semibold text-gray-900 mb-4">Pending Share Requests</h2>

      {requests.length === 0 ? (
        <p className="text-sm text-gray-500 py-8 text-center">No pending requests.</p>
      ) : (
        <div className="space-y-3">
          {requests.map((req) => (
            <div key={req.id} className="border border-gray-200 rounded-lg p-4 bg-white">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-900 font-mono">{req.skill_name}</span>
                <span className="text-xs text-gray-400">{new Date(req.created_at).toLocaleDateString()}</span>
              </div>
              <p className="text-xs text-gray-500 mb-3">
                From <span className="font-medium">{req.from_team_name}</span> to <span className="font-medium">{req.to_team_name}</span>
              </p>
              <div className="flex gap-2">
                <button
                  onClick={() => handleResolve(req.id, "approved")}
                  disabled={resolving === req.id}
                  className="px-3 py-1 bg-green-600 text-white text-xs font-medium rounded hover:bg-green-700 disabled:opacity-50 transition-colors"
                >
                  Approve
                </button>
                <button
                  onClick={() => handleResolve(req.id, "denied")}
                  disabled={resolving === req.id}
                  className="px-3 py-1 border border-gray-300 text-gray-700 text-xs font-medium rounded hover:bg-gray-50 disabled:opacity-50 transition-colors"
                >
                  Deny
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
