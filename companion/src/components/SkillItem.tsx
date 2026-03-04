import { useState } from "react";
import type { Skill } from "../hooks/useSkills";

interface SkillItemProps {
  skill: Skill;
}

export default function SkillItem({ skill }: SkillItemProps) {
  const [expanded, setExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  const copyCommand = async (e: React.MouseEvent) => {
    e.stopPropagation();
    await navigator.clipboard.writeText(`/locker ${skill.name}`);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div
      className="border border-gray-200 rounded-md bg-white hover:border-gray-300 transition-colors"
    >
      <div
        className="flex items-center justify-between px-4 py-3 cursor-pointer select-none"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-xs text-gray-400">
            {expanded ? "\u25BC" : "\u25B6"}
          </span>
          <span className="font-mono text-sm text-gray-900 truncate">
            {skill.name}
          </span>
        </div>

        <button
          onClick={copyCommand}
          className="shrink-0 ml-3 px-3 py-1 text-xs font-medium rounded border transition-colors bg-gray-50 border-gray-200 text-gray-700 hover:bg-gray-100"
        >
          {copied ? "Copied!" : "Copy"}
        </button>
      </div>

      {expanded && (
        <div className="px-4 pb-3 border-t border-gray-100">
          <p className="mt-2 text-sm text-gray-600">
            {skill.description || "No description available."}
          </p>
          <p className="mt-2 text-xs text-gray-400 font-mono">
            /locker {skill.name}
          </p>
        </div>
      )}
    </div>
  );
}
