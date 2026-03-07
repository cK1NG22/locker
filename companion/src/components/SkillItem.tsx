import { useState } from "react";
import type { Skill } from "../hooks/useSkills";
import FeedbackForm from "./FeedbackForm";

interface SkillItemProps {
  skill: Skill;
  convention?: string;
  token: string;
}

export default function SkillItem({ skill, convention = "/l", token }: SkillItemProps) {
  const [expanded, setExpanded] = useState(false);
  const [copied, setCopied] = useState(false);
  const [showFeedback, setShowFeedback] = useState(false);

  const copyCommand = async (e: React.MouseEvent) => {
    e.stopPropagation();
    await navigator.clipboard.writeText(`${convention} ${skill.name}`);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const isOpen = skill.content !== null;

  return (
    <div className="border border-gray-200 rounded-md bg-white hover:border-gray-300 transition-colors">
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

        {isOpen ? (
          <button
            onClick={copyCommand}
            className="shrink-0 ml-3 px-3 py-1 text-xs font-medium rounded border transition-colors bg-gray-50 border-gray-200 text-gray-700 hover:bg-gray-100"
          >
            {copied ? "Copied!" : "Copy"}
          </button>
        ) : (
          <span className="shrink-0 ml-3 text-xs text-gray-400 border border-gray-200 rounded px-2 py-1">
            Content hidden
          </span>
        )}
      </div>

      {expanded && (
        <div className="px-4 pb-3 border-t border-gray-100">
          <p className="mt-2 text-sm text-gray-600">
            {skill.description || "No description available."}
          </p>
          {isOpen && (
            <>
              <pre className="mt-2 text-xs font-mono bg-gray-50 rounded p-3 overflow-auto">
                {skill.content}
              </pre>
              <p className="mt-2 text-xs text-gray-400 font-mono">
                /locker {skill.name}
              </p>
              {skill.id && !showFeedback && (
                <button
                  onClick={() => setShowFeedback(true)}
                  className="mt-2 px-3 py-1 text-xs font-medium rounded border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors"
                >
                  Give feedback
                </button>
              )}
              {skill.id && showFeedback && (
                <FeedbackForm
                  skillId={skill.id}
                  skillName={skill.name}
                  token={token}
                  onClose={() => setShowFeedback(false)}
                />
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
