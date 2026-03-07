import { useState, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useSkills } from "../../hooks/useSkills";

interface SelectedFile {
  path: string;
  content: string;
  isMain: boolean;
}

function autoDetectMain(fileList: SelectedFile[]): SelectedFile[] {
  if (fileList.length === 0 || fileList.some((f) => f.isMain)) return fileList;
  const mdIndex = fileList.findIndex((f) => f.path.endsWith(".md"));
  const mainIndex = mdIndex >= 0 ? mdIndex : 0;
  return fileList.map((f, i) => ({ ...f, isMain: i === mainIndex }));
}

function stripCommonRoot(files: SelectedFile[]): SelectedFile[] {
  if (files.length < 2 || !files[0].path.includes("/")) return files;
  const root = files[0].path.split("/")[0] + "/";
  if (!files.every((f) => f.path.startsWith(root))) return files;
  return files.map((f) => ({ ...f, path: f.path.slice(root.length) }));
}

export default function SkillUpload() {
  const navigate = useNavigate();
  const { createSkill, deployFolder } = useSkills();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const folderInputRef = useRef<HTMLInputElement>(null);
  const nameRef = useRef("");

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [scope, setScope] = useState<"team" | "personal">("team");
  const [files, setFiles] = useState<SelectedFile[]>([]);
  const [dragging, setDragging] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Keep ref in sync so readFileObjects doesn't depend on name
  nameRef.current = name;

  const addFiles = useCallback((newFiles: SelectedFile[]) => {
    setFiles((prev) => {
      const existing = new Set(prev.map((f) => f.path));
      const unique = newFiles.filter((f) => !existing.has(f.path));
      return autoDetectMain([...prev, ...unique]);
    });
    setError(null);
  }, []);

  const readFileObjects = useCallback(
    async (fileList: File[]) => {
      const results: SelectedFile[] = [];
      await Promise.all(
        fileList.map(
          (file) =>
            new Promise<void>((resolve) => {
              const path = file.webkitRelativePath || file.name;
              const reader = new FileReader();
              reader.onload = (ev) => {
                results.push({
                  path,
                  content: ev.target?.result as string,
                  isMain: false,
                });
                resolve();
              };
              reader.onerror = () => {
                console.warn(`Failed to read file: ${path}`);
                resolve();
              };
              reader.readAsText(file);
            }),
        ),
      );

      if (results.length === 0) {
        setError("Could not read any of the selected files.");
        return;
      }

      const cleaned = stripCommonRoot(results);

      if (!nameRef.current) {
        if (cleaned.length === 1) {
          setName(cleaned[0].path.replace(/\.[^.]+$/, ""));
        } else if (fileList[0]?.webkitRelativePath) {
          setName(fileList[0].webkitRelativePath.split("/")[0]);
        }
      }

      addFiles(cleaned);
    },
    [addFiles],
  );

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const selected = e.target.files;
      if (!selected || selected.length === 0) return;
      readFileObjects(Array.from(selected));
      e.target.value = "";
    },
    [readFileObjects],
  );

  const handleDrop = useCallback(
    async (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);

      const items = e.dataTransfer.items;
      if (!items) return;

      const collected: File[] = [];

      const readEntry = (entry: FileSystemEntry): Promise<void> =>
        new Promise((resolve) => {
          if (entry.isFile) {
            (entry as FileSystemFileEntry).file((file) => {
              Object.defineProperty(file, "webkitRelativePath", {
                value: entry.fullPath.replace(/^\//, ""),
              });
              collected.push(file);
              resolve();
            });
          } else if (entry.isDirectory) {
            (entry as FileSystemDirectoryEntry).createReader().readEntries(
              async (entries) => {
                await Promise.all(entries.map(readEntry));
                resolve();
              },
            );
          } else {
            resolve();
          }
        });

      const entries: FileSystemEntry[] = [];
      for (let i = 0; i < items.length; i++) {
        const entry = items[i].webkitGetAsEntry?.();
        if (entry) entries.push(entry);
      }

      await Promise.all(entries.map(readEntry));
      if (collected.length > 0) readFileObjects(collected);
    },
    [readFileObjects],
  );

  const setMainFile = (path: string) => {
    setFiles((prev) => prev.map((f) => ({ ...f, isMain: f.path === path })));
  };

  const removeFile = (path: string) => {
    setFiles((prev) => {
      const updated = prev.filter((f) => f.path !== path);
      return updated.some((f) => f.isMain) ? updated : autoDetectMain(updated);
    });
  };

  const clearAll = () => {
    setFiles([]);
    setName("");
    setDescription("");
    setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmedName = name.trim();
    if (!trimmedName || files.length === 0) return;

    const mainFile = files.find((f) => f.isMain);
    if (!mainFile) return;

    setSaving(true);
    setError(null);

    const payload = {
      name: trimmedName,
      content: mainFile.content,
      description: description.trim() || undefined,
      scope,
    };

    try {
      if (files.length === 1) {
        await createSkill(payload);
      } else {
        await deployFolder({
          ...payload,
          files: files
            .filter((f) => !f.isMain)
            .map((f) => ({ path: f.path, content: f.content })),
        });
      }
      navigate("/skills");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="max-w-xl">
      <button
        onClick={() => navigate("/skills")}
        className="text-sm text-gray-500 hover:text-gray-700 mb-4 transition-colors"
      >
        &larr; Back to skills
      </button>

      <h2 className="text-lg font-semibold text-gray-900 mb-4">Upload Skill</h2>

      {/* Scope selector */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-1">Scope</label>
        <div className="flex gap-3">
          {(["team", "personal"] as const).map((s) => (
            <label key={s} className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
              <input
                type="radio"
                name="scope"
                value={s}
                checked={scope === s}
                onChange={() => setScope(s)}
                className="accent-blue-600"
              />
              {s === "team" ? "Team" : "Personal"}
              <span className="text-gray-400 text-xs">
                ({s === "team" ? "visible to all admins" : "only visible to you"})
              </span>
            </label>
          ))}
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Drop zone */}
        <div
          className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
            dragging ? "border-blue-400 bg-blue-50" : "border-gray-300 hover:border-gray-400"
          }`}
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
        >
          <p className="text-sm text-gray-600">Drop files or folders here</p>
          <p className="text-xs text-gray-400 mt-1">or use the buttons below to browse</p>
        </div>

        {/* Browse buttons */}
        <div className="flex gap-3">
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="flex-1 py-2 px-4 border border-gray-300 text-sm font-medium rounded-md text-gray-700 hover:bg-gray-50 transition-colors"
          >
            Browse files
          </button>
          <button
            type="button"
            onClick={() => folderInputRef.current?.click()}
            className="flex-1 py-2 px-4 border border-gray-300 text-sm font-medium rounded-md text-gray-700 hover:bg-gray-50 transition-colors"
          >
            Browse folder
          </button>
        </div>

        {/* Hidden inputs */}
        <input ref={fileInputRef} type="file" multiple className="hidden" onChange={handleInputChange} />
        <input
          ref={folderInputRef}
          type="file"
          className="hidden"
          /* @ts-expect-error webkitdirectory is not in React types */
          webkitdirectory=""
          onChange={handleInputChange}
        />

        {/* File list */}
        {files.length > 0 && (
          <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm font-medium text-gray-700">
                {files.length} file{files.length !== 1 ? "s" : ""} selected
              </span>
              <button
                type="button"
                onClick={clearAll}
                className="text-xs text-gray-400 hover:text-gray-600 transition-colors"
              >
                Clear all
              </button>
            </div>
            <ul className="space-y-1">
              {files.map((f) => (
                <li key={f.path} className="flex items-center justify-between text-sm group">
                  <button
                    type="button"
                    onClick={() => setMainFile(f.path)}
                    className={`flex items-center gap-2 text-left font-mono truncate ${
                      f.isMain ? "text-blue-600 font-medium" : "text-gray-500 hover:text-gray-700"
                    }`}
                    title={f.isMain ? "Main file" : "Click to set as main file"}
                  >
                    <span className={`inline-block w-2 h-2 rounded-full flex-shrink-0 ${
                      f.isMain ? "bg-blue-600" : "bg-gray-300"
                    }`} />
                    {f.path}
                  </button>
                  <button
                    type="button"
                    onClick={() => removeFile(f.path)}
                    className="text-gray-300 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-all ml-2 flex-shrink-0"
                    title="Remove file"
                  >
                    &times;
                  </button>
                </li>
              ))}
            </ul>
            <p className="text-xs text-gray-400 mt-2">
              Click a file to set it as the main skill content
            </p>
          </div>
        )}

        {/* Name */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. email-style"
            className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono"
          />
        </div>

        {/* Description */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Description <span className="text-gray-400 font-normal">(optional)</span>
          </label>
          <input
            type="text"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Brief description of what this skill does"
            className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <button
          type="submit"
          disabled={!name.trim() || files.length === 0 || saving}
          className="w-full py-2 px-4 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {saving ? "Uploading..." : files.length > 1 ? `Upload skill (${files.length} files)` : "Upload skill"}
        </button>
      </form>
    </div>
  );
}
