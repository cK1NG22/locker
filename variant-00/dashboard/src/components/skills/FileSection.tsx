import { useState, useCallback } from "react";
import type { SkillFileMeta, SkillFileFull } from "../../hooks/useSkills";

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  const val = bytes / Math.pow(1024, i);
  return `${val.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

interface FileSectionProps {
  skillId: string;
  files: SkillFileMeta[];
  onFilesChange: (updater: (files: SkillFileMeta[]) => SkillFileMeta[]) => void;
  getSkillFile: (skillId: string, fileId: string) => Promise<SkillFileFull>;
  uploadSkillFile: (skillId: string, body: { path: string; content: string }) => Promise<SkillFileMeta>;
  deleteSkillFile: (skillId: string, fileId: string) => Promise<void>;
}

export default function FileSection({
  skillId,
  files,
  onFilesChange,
  getSkillFile,
  uploadSkillFile,
  deleteSkillFile,
}: FileSectionProps) {
  const [expandedFileId, setExpandedFileId] = useState<string | null>(null);
  const [expandedFileContent, setExpandedFileContent] = useState<string | null>(null);
  const [loadingFileId, setLoadingFileId] = useState<string | null>(null);
  const [showAddFile, setShowAddFile] = useState(false);
  const [newFilePath, setNewFilePath] = useState("");
  const [newFileContent, setNewFileContent] = useState("");
  const [addingFile, setAddingFile] = useState(false);

  const handleViewFile = useCallback(
    async (fileId: string) => {
      if (expandedFileId === fileId) {
        setExpandedFileId(null);
        setExpandedFileContent(null);
        return;
      }
      setLoadingFileId(fileId);
      try {
        const file: SkillFileFull = await getSkillFile(skillId, fileId);
        setExpandedFileId(fileId);
        setExpandedFileContent(file.content);
      } catch (e) {
        alert(e instanceof Error ? e.message : "Failed to load file");
      } finally {
        setLoadingFileId(null);
      }
    },
    [skillId, expandedFileId, getSkillFile],
  );

  const handleDeleteFile = useCallback(
    async (fileId: string, filePath: string) => {
      if (!confirm(`Delete reference file "${filePath}"?`)) return;
      try {
        await deleteSkillFile(skillId, fileId);
        onFilesChange((prev) => prev.filter((f) => f.id !== fileId));
        if (expandedFileId === fileId) {
          setExpandedFileId(null);
          setExpandedFileContent(null);
        }
      } catch (e) {
        alert(e instanceof Error ? e.message : "Delete failed");
      }
    },
    [skillId, expandedFileId, deleteSkillFile, onFilesChange],
  );

  const handleAddFile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newFilePath.trim() || !newFileContent.trim()) return;
    setAddingFile(true);
    try {
      const created: SkillFileMeta = await uploadSkillFile(skillId, {
        path: newFilePath.trim(),
        content: newFileContent.trim(),
      });
      onFilesChange((prev) => [...prev, created]);
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
    if (!newFilePath) setNewFilePath(file.name);
    const reader = new FileReader();
    reader.onload = (ev) => setNewFileContent(ev.target?.result as string);
    reader.readAsText(file);
    e.target.value = "";
  };

  return (
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
  );
}
