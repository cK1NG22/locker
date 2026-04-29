import { Link } from "react-router-dom";
import { useSkills } from "../../hooks/useSkills";

export default function SkillList() {
  const { skills, loading, error, deleteSkill } = useSkills();

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Delete skill "${name}"?`)) return;
    try {
      await deleteSkill(id);
    } catch (e) {
      alert(e instanceof Error ? e.message : "Delete failed");
    }
  };

  if (loading) {
    return <p className="text-sm text-gray-500">Loading skills...</p>;
  }

  if (error) {
    return <p className="text-sm text-red-600">{error}</p>;
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-lg font-semibold text-gray-900">Skills</h2>
        <Link
          to="/skills/upload"
          className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 transition-colors"
        >
          Upload skill
        </Link>
      </div>

      {skills.length === 0 ? (
        <p className="text-sm text-gray-500 py-8 text-center">
          No skills yet. Upload one to get started.
        </p>
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
                      <Link
                        to={`/skills/${skill.id}`}
                        className="font-mono text-blue-600 hover:underline"
                      >
                        {skill.name}
                      </Link>
                      {skill.scope === "personal" && (
                        <span className="text-xs px-1.5 py-0.5 bg-amber-100 text-amber-700 rounded font-medium">
                          Personal
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-gray-500 truncate max-w-xs">
                    {skill.description || "--"}
                  </td>
                  <td className="px-4 py-3 text-gray-400 text-xs">
                    {skill.uploaded_by_name || "--"}
                  </td>
                  <td className="px-4 py-3 text-gray-400">
                    {new Date(skill.updated_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => handleDelete(skill.id, skill.name)}
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
