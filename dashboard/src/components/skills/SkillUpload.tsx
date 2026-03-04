import { useState, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useSkills } from "../../hooks/useSkills";

type UploadMode = "single" | "folder";

interface FolderFile {
  path: string;
  content: string;
}

interface FolderPreview {
  mainFile: string;
  mainContent: string;
  referenceFiles: FolderFile[];
}

export default function SkillUpload() {
  const navigate = useNavigate();
  const { createSkill, deployFolder } = useSkills();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const folderInputRef = useRef<HTMLInputElement>(null);

  const [mode, setMode] = useState<UploadMode>("single");

  // Single-file state
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [content, setContent] = useState("");
  const [fileName, setFileName] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);

  // Folder state
  const [folderName, setFolderName] = useState("");
  const [folderDescription, setFolderDescription] = useState("");
  const [folderPreview, setFolderPreview] = useState<FolderPreview | null>(null);

  // Shared state
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // --- Single-file handlers (unchanged) ---

  const readFile = useCallback((file: File) => {
    setFileName(file.name);
    if (!name) {
      setName(file.name.replace(/\.[^.]+$/, ""));
    }
    const reader = new FileReader();
    reader.onload = (e) => {
      setContent(e.target?.result as string);
    };
    reader.readAsText(file);
  }, [name]);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) readFile(file);
    },
    [readFile],
  );

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) readFile(file);
  };

  const handleSubmitSingle = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !content.trim()) return;

    setSaving(true);
    setError(null);
    try {
      await createSkill({
        name: name.trim(),
        content: content.trim(),
        description: description.trim() || undefined,
      });
      navigate("/skills");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setSaving(false);
    }
  };

  // --- Folder handlers ---

  const handleFolderSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    setError(null);

    const fileList = Array.from(files);

    // Read all files as text
    const readResults: { path: string; content: string; name: string }[] = [];

    await Promise.all(
      fileList.map(
        (file) =>
          new Promise<void>((resolve) => {
            // webkitRelativePath gives us "folderName/subfolder/file.ext"
            const relativePath = file.webkitRelativePath || file.name;
            const reader = new FileReader();
            reader.onload = (ev) => {
              readResults.push({
                path: relativePath,
                content: ev.target?.result as string,
                name: file.name,
              });
              resolve();
            };
            reader.onerror = () => resolve(); // skip unreadable files
            reader.readAsText(file);
          }),
      ),
    );

    if (readResults.length === 0) {
      setError("No readable files found in the selected folder");
      return;
    }

    // Detect main .md file:
    // 1. Find all .md files
    // 2. Prefer the one whose stem matches a subfolder name (skill convention)
    // 3. Otherwise take the first .md file
    const mdFiles = readResults.filter((f) => f.name.endsWith(".md"));
    const subfolderNames = new Set(
      readResults
        .map((f) => {
          const parts = f.path.split("/");
          // parts[0] is the root folder; parts[1] could be a subfolder
          return parts.length > 2 ? parts[1] : null;
        })
        .filter(Boolean),
    );

    let mainFile =
      mdFiles.find((f) => {
        const stem = f.name.replace(/\.md$/, "");
        return subfolderNames.has(stem);
      }) || mdFiles[0];

    if (!mainFile) {
      // No .md file at all — just pick the first file
      mainFile = readResults[0];
    }

    const referenceFiles = readResults
      .filter((f) => f.path !== mainFile!.path)
      .map((f) => ({ path: f.path, content: f.content }));

    // Strip the root folder prefix from all paths for cleaner display
    const rootPrefix = readResults[0].path.split("/")[0] + "/";
    const cleanPath = (p: string) => (p.startsWith(rootPrefix) ? p.slice(rootPrefix.length) : p);

    setFolderPreview({
      mainFile: cleanPath(mainFile.path),
      mainContent: mainFile.content,
      referenceFiles: referenceFiles.map((f) => ({
        path: cleanPath(f.path),
        content: f.content,
      })),
    });

    if (!folderName) {
      // Use root folder name as skill name
      const rootFolder = readResults[0].path.split("/")[0];
      setFolderName(rootFolder);
    }
  };

  const handleSubmitFolder = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!folderPreview || !folderName.trim()) return;

    setSaving(true);
    setError(null);
    try {
      await deployFolder({
        name: folderName.trim(),
        content: folderPreview.mainContent,
        description: folderDescription.trim() || undefined,
        files: folderPreview.referenceFiles,
      });
      navigate("/skills");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Folder upload failed");
    } finally {
      setSaving(false);
    }
  };

  const clearFolder = () => {
    setFolderPreview(null);
    setFolderName("");
    setFolderDescription("");
    if (folderInputRef.current) folderInputRef.current.value = "";
  };

  // --- Shared ---

  const switchMode = (newMode: UploadMode) => {
    setMode(newMode);
    setError(null);
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

      {/* Mode toggle */}
      <div className="flex border-b border-gray-200 mb-6">
        <button
          onClick={() => switchMode("single")}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            mode === "single"
              ? "border-blue-600 text-blue-600"
              : "border-transparent text-gray-500 hover:text-gray-700"
          }`}
        >
          Single file
        </button>
        <button
          onClick={() => switchMode("folder")}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            mode === "folder"
              ? "border-blue-600 text-blue-600"
              : "border-transparent text-gray-500 hover:text-gray-700"
          }`}
        >
          Folder
        </button>
      </div>

      {/* ===== Single-file mode ===== */}
      {mode === "single" && (
        <form onSubmit={handleSubmitSingle} className="space-y-4">
          {/* Drop zone */}
          <div
            className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
              dragging
                ? "border-blue-400 bg-blue-50"
                : "border-gray-300 hover:border-gray-400"
            }`}
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              ref={fileInputRef}
              type="file"
              className="hidden"
              accept=".txt,.md,.yaml,.yml,.json"
              onChange={handleFileSelect}
            />
            {fileName ? (
              <p className="text-sm text-gray-700">
                <span className="font-medium">{fileName}</span>
                <span className="text-gray-400 ml-2">({content.length} chars)</span>
              </p>
            ) : (
              <div>
                <p className="text-sm text-gray-600">
                  Drop a skill file here or click to browse
                </p>
                <p className="text-xs text-gray-400 mt-1">
                  .txt, .md, .yaml, .json
                </p>
              </div>
            )}
          </div>

          {/* Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Name
            </label>
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
            disabled={!name.trim() || !content.trim() || saving}
            className="w-full py-2 px-4 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {saving ? "Uploading..." : "Upload skill"}
          </button>
        </form>
      )}

      {/* ===== Folder mode ===== */}
      {mode === "folder" && (
        <form onSubmit={handleSubmitFolder} className="space-y-4">
          {/* Hidden directory input */}
          <input
            ref={folderInputRef}
            type="file"
            className="hidden"
            /* @ts-expect-error webkitdirectory is not in React types */
            webkitdirectory=""
            onChange={handleFolderSelect}
          />

          {/* Folder picker */}
          {!folderPreview ? (
            <div
              className="border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors border-gray-300 hover:border-gray-400"
              onClick={() => folderInputRef.current?.click()}
            >
              <p className="text-sm text-gray-600">
                Click to select a skill folder
              </p>
              <p className="text-xs text-gray-400 mt-1">
                The folder should contain a main .md file and optional reference files
              </p>
            </div>
          ) : (
            <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm font-medium text-gray-700">Folder preview</span>
                <button
                  type="button"
                  onClick={clearFolder}
                  className="text-xs text-gray-400 hover:text-gray-600 transition-colors"
                >
                  Clear
                </button>
              </div>
              <div className="space-y-1 text-sm">
                <p className="text-gray-700">
                  <span className="font-medium">Main:</span>{" "}
                  <span className="font-mono text-blue-600">{folderPreview.mainFile}</span>
                </p>
                <p className="text-gray-500">
                  {folderPreview.referenceFiles.length} reference file
                  {folderPreview.referenceFiles.length !== 1 ? "s" : ""}
                </p>
                {folderPreview.referenceFiles.length > 0 && (
                  <ul className="mt-2 space-y-0.5 pl-4 text-xs text-gray-400 font-mono">
                    {folderPreview.referenceFiles.map((f) => (
                      <li key={f.path}>{f.path}</li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          )}

          {/* Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Name
            </label>
            <input
              type="text"
              value={folderName}
              onChange={(e) => setFolderName(e.target.value)}
              placeholder="e.g. research-agent"
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
              value={folderDescription}
              onChange={(e) => setFolderDescription(e.target.value)}
              placeholder="Brief description of what this skill does"
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}

          <button
            type="submit"
            disabled={!folderPreview || !folderName.trim() || saving}
            className="w-full py-2 px-4 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {saving ? "Deploying folder..." : "Deploy skill folder"}
          </button>
        </form>
      )}
    </div>
  );
}
