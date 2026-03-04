import { Link } from "react-router-dom";
import { useTeams } from "../../hooks/useTeams";

export default function TeamList() {
  const { teams, loading, error, deleteTeam } = useTeams();

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Delete team "${name}"? Employees using this team's token will lose access.`)) return;
    try {
      await deleteTeam(id);
    } catch (e) {
      alert(e instanceof Error ? e.message : "Delete failed");
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
        <Link
          to="/teams/new"
          className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 transition-colors"
        >
          Create team
        </Link>
      </div>

      {teams.length === 0 ? (
        <p className="text-sm text-gray-500 py-8 text-center">
          No teams yet. Create one to get started.
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
    </div>
  );
}
