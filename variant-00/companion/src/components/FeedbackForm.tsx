import { useState } from "react";

interface FeedbackFormProps {
  skillId: string;
  skillName: string;
  token: string;
  onClose: () => void;
}

const FIELDS = [
  { key: "observed", label: "What happened", placeholder: "Describe the output you got" },
  { key: "expected", label: "What I expected", placeholder: "What the output should have looked like" },
  { key: "cause", label: "Why I think it happened", placeholder: "What in the skill might be causing this" },
  { key: "suggestion", label: "Suggested fix", placeholder: "Optional — your idea for how to improve" },
] as const;

type FieldKey = (typeof FIELDS)[number]["key"];

export default function FeedbackForm({ skillId, skillName, token, onClose }: FeedbackFormProps) {
  const [values, setValues] = useState<Record<FieldKey, string>>({
    observed: "", expected: "", cause: "", suggestion: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<"success" | "error" | null>(null);

  const setField = (key: FieldKey, val: string) =>
    setValues((prev) => ({ ...prev, [key]: val }));

  const hasContent = values.observed.trim() || values.expected.trim() || values.cause.trim();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!hasContent) return;

    const feedbackText = FIELDS
      .filter(({ key }) => values[key].trim())
      .map(({ key, label }) => `${label}: ${values[key].trim()}`)
      .join("\n");

    setSubmitting(true);
    try {
      const res = await fetch(`/api/v1/skills/${skillId}/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Team-Token": token },
        body: JSON.stringify({ feedback_text: feedbackText }),
      });
      if (!res.ok) throw new Error("Failed");
      setResult("success");
      setTimeout(onClose, 1500);
    } catch {
      setResult("error");
    } finally {
      setSubmitting(false);
    }
  };

  if (result === "success") {
    return (
      <div className="mt-3 p-3 bg-green-50 border border-green-200 rounded text-sm text-green-700">
        Feedback submitted for {skillName}. Thank you!
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="mt-3 space-y-2">
      <p className="text-xs font-medium text-gray-500">
        Feedback for <span className="text-gray-700">{skillName}</span>
      </p>
      {FIELDS.map(({ key, label, placeholder }) => (
        <textarea
          key={key}
          placeholder={`${label} — ${placeholder}`}
          value={values[key]}
          onChange={(e) => setField(key, e.target.value)}
          className="w-full text-xs border border-gray-200 rounded p-2 resize-none"
          rows={2}
        />
      ))}
      {result === "error" && (
        <p className="text-xs text-red-600">Failed to submit. Try again.</p>
      )}
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={submitting || !hasContent}
          className="px-3 py-1 text-xs font-medium rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {submitting ? "Submitting..." : "Submit"}
        </button>
        <button
          type="button"
          onClick={onClose}
          className="px-3 py-1 text-xs font-medium rounded border border-gray-200 text-gray-600 hover:bg-gray-50"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}
