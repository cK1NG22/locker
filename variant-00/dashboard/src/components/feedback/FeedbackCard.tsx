import { useState } from "react";
import type { FeedbackItem } from "../../hooks/useFeedback";
import { copyToClipboard } from "../../lib/clipboard";

interface FeedbackCardProps {
  item: FeedbackItem;
  onUpdateStatus: (id: string, status: "reviewed" | "applied") => Promise<void>;
}

const statusColors: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-800",
  reviewed: "bg-blue-100 text-blue-800",
  applied: "bg-green-100 text-green-800",
};

export default function FeedbackCard({ item, onUpdateStatus }: FeedbackCardProps) {
  const [copied, setCopied] = useState(false);
  const [updating, setUpdating] = useState(false);

  const copyText = () => {
    const text = `Skill: ${item.skill_name || "Unknown"}\n\n${item.feedback_text}`;
    copyToClipboard(text, setCopied);
  };

  const handleStatus = async (status: "reviewed" | "applied") => {
    setUpdating(true);
    try {
      await onUpdateStatus(item.id, status);
    } finally {
      setUpdating(false);
    }
  };

  const date = new Date(item.created_at).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });

  return (
    <div className="flex border border-gray-200 rounded-lg overflow-hidden bg-white">
      {/* Left: Submitter info */}
      <div className="w-48 shrink-0 p-4 bg-gray-50 border-r border-gray-200 flex flex-col justify-between">
        <div>
          <p className="text-xs text-gray-500">Team</p>
          <p className="text-sm font-medium text-gray-900 mt-0.5">
            {item.submitter_team_name || "Unknown"}
          </p>
          <p className="text-xs text-gray-400 mt-2">{date}</p>
          <span
            className={`inline-block mt-2 px-2 py-0.5 text-xs font-medium rounded ${statusColors[item.status] || "bg-gray-100 text-gray-600"}`}
          >
            {item.status}
          </span>
        </div>
        <div className="flex flex-col gap-1 mt-3">
          {item.status !== "reviewed" && (
            <button
              onClick={() => handleStatus("reviewed")}
              disabled={updating}
              className="text-xs px-2 py-1 rounded border border-gray-300 text-gray-600 hover:bg-gray-100 disabled:opacity-50"
            >
              Mark Reviewed
            </button>
          )}
          {item.status !== "applied" && (
            <button
              onClick={() => handleStatus("applied")}
              disabled={updating}
              className="text-xs px-2 py-1 rounded border border-blue-300 text-blue-600 hover:bg-blue-50 disabled:opacity-50"
            >
              Mark Applied
            </button>
          )}
        </div>
      </div>

      {/* Right: Feedback content */}
      <div className="flex-1 p-4 flex flex-col">
        <div className="flex items-start justify-between">
          <p className="text-sm font-medium text-gray-900">
            Skill: {item.skill_name || "Unknown"}
          </p>
          <button
            onClick={copyText}
            className="shrink-0 ml-3 px-3 py-1 text-xs font-medium rounded border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors"
          >
            {copied ? "Copied!" : "Copy feedback"}
          </button>
        </div>
        <pre className="mt-3 text-sm text-gray-700 whitespace-pre-wrap font-sans flex-1">
          {item.feedback_text}
        </pre>
      </div>
    </div>
  );
}
