import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTeams } from "../../hooks/useTeams";

export default function TeamForm() {
  const navigate = useNavigate();
  const { createTeam } = useTeams();

  const [name, setName] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    setSaving(true);
    setError(null);
    try {
      const result = await createTeam(name.trim());
      navigate(`/teams/${result.id}`, { state: { newToken: result } });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Create failed");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="max-w-sm">
      <button
        onClick={() => navigate("/teams")}
        className="text-sm text-gray-500 hover:text-gray-700 mb-4 transition-colors"
      >
        &larr; Back to teams
      </button>

      <h2 className="text-lg font-semibold text-gray-900 mb-6">Create Team</h2>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Team name
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Legal, Sales, Engineering"
            className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            autoFocus
          />
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <button
          type="submit"
          disabled={!name.trim() || saving}
          className="w-full py-2 px-4 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {saving ? "Creating..." : "Create team"}
        </button>
      </form>
    </div>
  );
}
