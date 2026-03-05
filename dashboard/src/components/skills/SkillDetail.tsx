import { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  useSkills,
  type SkillFull,
  type SkillFileMeta,
  type SkillFileFull,
} from "../../hooks/useSkills";
import { useAuth } from "../../context/AuthContext";
import { useTeams, type TeamSummary } from "../../hooks/useTeams";

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  const val = bytes / Math.pow(1024, i);
  return `${val.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

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
  } = useSkills();
  const { user } = useAuth();
  const { teams } = useTeams();
  const { copyToTeam } = useSkills();

  const [skill, setSkill] = useState<SkillFull | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Inline edit state
  const [editingName, setEditingName] = useState(false);
  const [editingDesc, setEditingDesc] = useState(false);
  const [nameValue, setNameValue] = useState("");
  const [descValue, setDescValue] = useState("");
  const [saving, setSaving] = useState(false);

  // Reference files state
  const [expandedFileId, setExpandedFileId] = useState<string | null>(null);
  const [expandedFileContent, setExpandedFileContent] = useState<string | null>(null);
  const [loadingFileId, setLoadingFileId] = useState<string | null>(null);
  const [showAddFile, setShowAddFile] = useState(false);
  const [newFilePath, setNewFilePath] = useState("");
  const [newFileContent, setNewFileContent] = useState("");
  const [addingFile, setAddingFile] = useState(false);

  // Share to team state
  const [showShareModal, setShowShareModal] = useState(false);
  const [shareTeamId, setShareTeamId] = useState("");
  const [sharing, setSharing] = useState(false);
  const [shareError, setShareError] = useState<string | null>(null);
  const [shareSuccess, setShareSuccess] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    getSkill(id)
      .then((s) => {
        setSkill(s);
        setNameValue(s.name);
        setDescValue(s.description || "");
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load skill"))
      .finally(() => setLoading(false));
  }, [id, getSkill]);

  const saveName = async () => {
    if (!id || !nameValue.trim() || nameValue === skill?.name) {
      setEditingName(false);
      return;
    }
    setSaving(true);
    try {
      await updateSkill(id, { name: nameValue.trim() });
      setSkill((s) => s ? { ...s, name: nameValue.trim() } : s);
      setEditingName(false);
    } catch (e) {
      alert(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const saveDesc = async () => {
    if (!id || descValue === (skill?.description || "")) {
      setEditingDesc(false);
      return;
    }
    setSaving(true);
    try {
      await updateSkill(id, { description: descValue });
      setSkill((s) => s ? { ...s, description: descValue } : s);
      setEditingDesc(false);
    } catch (e) {
      alert(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!id || !confirm(`Delete skill "${skill?.name}"?`)) return;
    try {
      await deleteSkill(id);
      navigate("/skills");
    } catch (e) {
      alert(e instanceof Error ? e.message : "Delete failed");
    }
  };

  // --- Reference file handlers ---

  const handleViewFile = useCallback(
    async (fileId: string) => {
      if (!id) return;

      // Toggle off if already expanded
      if (expandedFileId === fileId) {
        setExpandedFileId(null);
        setExpandedFileContent(null);
        return;
      }

      setLoadingFileId(fileId);
      try {
        const file: SkillFileFull = await getSkillFile(id, fileId);
        setExpandedFileId(fileId);
        setExpandedFileContent(file.content);
      } catch (e) {
        alert(e instanceof Error ? e.message : "Failed to load file");
      } finally {
        setLoadingFileId(null);
      }
    },
    [id, expandedFileId, getSkillFile],
  );

  const handleDeleteFile = useCallback(
    async (fileId: string, filePath: string) => {
      if (!id || !confirm(`Delete reference file "${filePath}"?`)) return;

      try {
        await deleteSkillFile(id, fileId);
        // Remove from local state
        setSkill((s) =>
          s
            ? {
                ...s,
                files: s.files.filter((f) => f.id !== fileId),
                file_count: s.file_count - 1,
              }
            : s,
        );
        // Collapse if this was the expanded file
        if (expandedFileId === fileId) {
          setExpandedFileId(null);
          setExpandedFileContent(null);
        }
      } catch (e) {
        alert(e instanceof Error ? e.message : "Delete failed");
      }
    },
    [id, expandedFileId, deleteSkillFile],
  );

  const handleAddFile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id || !newFilePath.trim() || !newFileContent.trim()) return;

    setAddingFile(true);
    try {
      const created: SkillFileMeta = await uploadSkillFile(id, {
        path: newFilePath.trim(),
        content: newFileContent.trim(),
      });
      // Add to local state
      setSkill((s) =>
        s
          ? {
              ...s,
              files: [...s.files, created],
              file_count: s.file_count + 1,
            }
          : s,
      );
      setNewFilePath("");
      setNewFileContent("");
      setShowAddFile(false);
    } catch (e) {
      alert(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setAddingFile(false);
    }
  };

  const handleAddFileFromDisk = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!newFilePath) {
      setNewFilePath(file.name);
    }
    const reader = new FileReader();
    reader.onload = (ev) => {
      setNewFileContent(ev.target?.result as string);
    };
    reader.readAsText(file);
  };

  const handleShare = async () => {
    if (!id || !shareTeamId) return;
    setSharing(true);
    setShareError(null);
    setShareSuccess(null);
    try {
      const result = await copyToTeam(id, shareTeamId);
      setShareSuccess(`Copied as new skill (ID: ${result.id})`);
      setShareTeamId("");
    } catch (e) {
      setShareError(e instanceof Error ? e.message : "Copy failed");
    } finally {
      setSharing(false);
    }
  };

  if (loading) return <p className="text-sm text-gray-500">Loading...</p>;
  if (error) return <p className="text-sm text-red-600">{error}</p>;
  if (!skill) return null;

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
        {editingName ? (
          <div className="flex items-center gap-2">
            <input
              value={nameValue}
              onChange={(e) => setNameValue(e.target.value)}
              className="text-lg font-semibold text-gray-900 font-mono border border-gray-300 rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
              autoFocus
              onKeyDown={(e) => {
                if (e.key === "Enter") saveName();
                if (e.key === "Escape") { setEditingName(false); setNameValue(skill.name); }
              }}
            />
            <button onClick={saveName} disabled={saving} className="text-sm text-blue-600 hover:underline">
              Save
            </button>
            <button onClick={() => { setEditingName(false); setNameValue(skill.name); }} className="text-sm text-gray-400 hover:underline">
              Cancel
            </button>
          </div>
        ) : (
          <h2
            className="text-lg font-semibold text-gray-900 font-mono cursor-pointer hover:text-blue-600 transition-colors"
            onClick={() => setEditingName(true)}
            title="Click to edit"
          >
            {skill.name}
          </h2>
        )}
      </div>

      {/* Description */}
      <div className="mb-6">
        <label className="text-xs text-gray-400 uppercase tracking-wide">Description</label>
        {editingDesc ? (
          <div className="mt-1 flex items-start gap-2">
            <input
              value={descValue}
              onChange={(e) => setDescValue(e.target.value)}
              className="flex-1 border border-gray-300 rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              autoFocus
              onKeyDown={(e) => {
                if (e.key === "Enter") saveDesc();
                if (e.key === "Escape") { setEditingDesc(false); setDescValue(skill.description || ""); }
              }}
            />
            <button onClick={saveDesc} disabled={saving} className="text-sm text-blue-600 hover:underline">
              Save
            </button>
            <button onClick={() => { setEditingDesc(false); setDescValue(skill.description || ""); }} className="text-sm text-gray-400 hover:underline">
              Cancel
            </button>
          </div>
        ) : (
          <p
            className="mt-1 text-sm text-gray-600 cursor-pointer hover:text-blue-600 transition-colors"
            onClick={() => setEditingDesc(true)}
            title="Click to edit"
          >
            {skill.description || "No description (click to add)"}
          </p>
        )}
      </div>

      {/* Content (read-only) */}
      <div className="mb-6">
        <label className="text-xs text-gray-400 uppercase tracking-wide">Content</label>
        <pre className="mt-1 bg-gray-900 text-gray-100 text-sm p-4 rounded-lg overflow-auto max-h-96 font-mono whitespace-pre-wrap">
          {skill.content}
        </pre>
      </div>

      {/* Reference Files */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <label className="text-xs text-gray-400 uppercase tracking-wide">
            Reference Files
            {files.length > 0 && (
              <span className="ml-1 text-gray-300">({files.length})</span>
            )}
          </label>
          <button
            type="button"
            onClick={() => setShowAddFile(!showAddFile)}
            className="text-xs text-blue-600 hover:text-blue-800 transition-colors"
          >
            {showAddFile ? "Cancel" : "+ Add reference file"}
          </button>
        </div>

        {/* Add file form */}
        {showAddFile && (
          <form onSubmit={handleAddFile} className="border border-gray-200 rounded-lg p-4 mb-3 bg-gray-50 space-y-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">File path</label>
              <input
                type="text"
                value={newFilePath}
                onChange={(e) => setNewFilePath(e.target.value)}
                placeholder="e.g. references/data-sources.md"
                className="w-full px-3 py-1.5 border border-gray-300 rounded text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="text-xs font-medium text-gray-600">Content</label>
                <label className="text-xs text-blue-600 hover:text-blue-800 cursor-pointer transition-colors">
                  Browse file
                  <input
                    type="file"
                    className="hidden"
                    accept=".txt,.md,.yaml,.yml,.json,.csv,.tsv"
                    onChange={handleAddFileFromDisk}
                  />
                </label>
              </div>
              <textarea
                value={newFileContent}
                onChange={(e) => setNewFileContent(e.target.value)}
                rows={4}
                placeholder="Paste file content or browse to select a file"
                className="w-full px-3 py-1.5 border border-gray-300 rounded text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-y"
              />
            </div>
            <button
              type="submit"
              disabled={!newFilePath.trim() || !newFileContent.trim() || addingFile}
              className="px-4 py-1.5 bg-blue-600 text-white text-sm font-medium rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {addingFile ? "Adding..." : "Add file"}
            </button>
          </form>
        )}

        {/* File list */}
        {files.length === 0 ? (
          <p className="text-sm text-gray-400 italic">No reference files</p>
        ) : (
          <div className="border border-gray-200 rounded-lg divide-y divide-gray-200">
            {files.map((file) => (
              <div key={file.id}>
                <div className="flex items-center justify-between px-4 py-2.5">
                  <div className="flex items-center gap-3 min-w-0">
                    <span className="text-sm font-mono text-gray-700 truncate">
                      {file.path}
                    </span>
                    <span className="text-xs text-gray-400 whitespace-nowrap">
                      {formatBytes(file.size_bytes)}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 ml-3 shrink-0">
                    <button
                      type="button"
                      onClick={() => handleViewFile(file.id)}
                      disabled={loadingFileId === file.id}
                      className="text-xs text-blue-600 hover:text-blue-800 disabled:opacity-50 transition-colors"
                    >
                      {loadingFileId === file.id
                        ? "Loading..."
                        : expandedFileId === file.id
                        ? "Hide"
                        : "View"}
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDeleteFile(file.id, file.path)}
                      className="text-xs text-red-500 hover:text-red-700 transition-colors"
                    >
                      Delete
                    </button>
                  </div>
                </div>

                {/* Expanded content */}
                {expandedFileId === file.id && expandedFileContent !== null && (
                  <div className="px-4 pb-3">
                    <pre className="bg-gray-900 text-gray-100 text-xs p-3 rounded-lg overflow-auto max-h-64 font-mono whitespace-pre-wrap">
                      {expandedFileContent}
                    </pre>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Share to team */}
      {canShare && (
        <div className="mb-6">
          <button
            type="button"
            onClick={() => { setShowShareModal(true); setShareError(null); setShareSuccess(null); }}
            className="text-sm text-blue-600 hover:text-blue-800 transition-colors"
          >
            Share to team...
          </button>

          {showShareModal && (
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
                  onClick={() => { setShowShareModal(false); setShareError(null); setShareSuccess(null); }}
                  className="px-3 py-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
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
