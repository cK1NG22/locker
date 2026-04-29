import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  useSkills,
  type SkillFull,
} from "../../hooks/useSkills";
import { useAuth } from "../../context/AuthContext";
import { useTeams } from "../../hooks/useTeams";
import EditableField from "./EditableField";
import FileSection from "./FileSection";
import ShareModal from "./ShareModal";

export default function SkillDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const {
    getSkill,
    updateSkill,
    deleteSkill,
    getSkillFile,
    uploadSkillFile,
    deleteSkillFile,
    copyToTeam,
  } = useSkills();
  const { user } = useAuth();
  const { teams } = useTeams();

  const [skill, setSkill] = useState<SkillFull | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    getSkill(id)
      .then((s) => setSkill(s))
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load skill"))
      .finally(() => setLoading(false));
  }, [id, getSkill]);

  const handleDelete = async () => {
    if (!id || !confirm(`Delete skill "${skill?.name}"?`)) return;
    try {
      await deleteSkill(id);
      navigate("/skills");
    } catch (e) {
      alert(e instanceof Error ? e.message : "Delete failed");
    }
  };

  if (loading) return <p className="text-sm text-gray-500">Loading...</p>;
  if (error) return <p className="text-sm text-red-600">{error}</p>;
  if (!skill || !id) return null;

  const files = skill.files ?? [];
  const isOwnPersonal = skill.scope === "personal" && skill.uploaded_by === user?.id;
  const isOpenTeam = skill.scope === "team" && skill.visibility === "open";
  const canShare = isOwnPersonal || isOpenTeam;

  return (
    <div className="max-w-3xl">
      <button
        onClick={() => navigate("/skills")}
        className="text-sm text-gray-500 hover:text-gray-700 mb-4 transition-colors"
      >
        &larr; Back to skills
      </button>

      {/* Name */}
      <div className="mb-4">
        <EditableField
          value={skill.name}
          onSave={async (v) => {
            await updateSkill(id, { name: v });
            setSkill((s) => s ? { ...s, name: v } : s);
          }}
          displayClassName="text-lg font-semibold text-gray-900 font-mono"
          inputClassName="text-lg font-semibold text-gray-900 font-mono border border-gray-300 rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
          as="h2"
        />
      </div>

      {/* Description */}
      <div className="mb-6">
        <label className="text-xs text-gray-400 uppercase tracking-wide">Description</label>
        <EditableField
          value={skill.description || ""}
          placeholder="No description (click to add)"
          onSave={async (v) => {
            await updateSkill(id, { description: v });
            setSkill((s) => s ? { ...s, description: v } : s);
          }}
          displayClassName="mt-1 text-sm text-gray-600"
          inputClassName="flex-1 border border-gray-300 rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {/* Content (read-only) */}
      <div className="mb-6">
        <label className="text-xs text-gray-400 uppercase tracking-wide">Content</label>
        <pre className="mt-1 bg-gray-900 text-gray-100 text-sm p-4 rounded-lg overflow-auto max-h-96 font-mono whitespace-pre-wrap">
          {skill.content}
        </pre>
      </div>

      {/* Reference Files */}
      <FileSection
        skillId={id}
        files={files}
        onFilesChange={(updater) =>
          setSkill((s) => s ? { ...s, files: updater(s.files ?? []), file_count: updater(s.files ?? []).length } : s)
        }
        getSkillFile={getSkillFile}
        uploadSkillFile={uploadSkillFile}
        deleteSkillFile={deleteSkillFile}
      />

      {/* Share to team */}
      {canShare && (
        <ShareModal skillId={id} teams={teams} copyToTeam={copyToTeam} />
      )}

      {/* Metadata + delete */}
      <div className="flex items-center justify-between text-xs text-gray-400 pt-4 border-t border-gray-200">
        <span>Created {new Date(skill.created_at).toLocaleString()}</span>
        <button
          onClick={handleDelete}
          className="text-red-500 hover:text-red-700 transition-colors"
        >
          Delete skill
        </button>
      </div>
    </div>
  );
}
