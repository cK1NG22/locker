import { useState } from "react";
import { useFeedback } from "../../hooks/useFeedback";
import FeedbackCard from "./FeedbackCard";

const TABS = [
  { label: "All", value: undefined },
  { label: "Pending", value: "pending" },
  { label: "Reviewed", value: "reviewed" },
  { label: "Applied", value: "applied" },
] as const;

export default function FeedbackList() {
  const { feedback, loading, error, refresh, updateStatus } = useFeedback();
  const [activeTab, setActiveTab] = useState<string | undefined>(undefined);

  const handleTabChange = (value: string | undefined) => {
    setActiveTab(value);
    refresh(value);
  };

  if (loading) {
    return <p className="text-sm text-gray-500 py-8">Loading feedback...</p>;
  }

  if (error) {
    return <p className="text-sm text-red-600 py-8">{error}</p>;
  }

  return (
    <div>
      <h1 className="text-lg font-semibold text-gray-900 mb-4">Feedback</h1>

      <div className="flex gap-1 mb-4">
        {TABS.map((tab) => (
          <button
            key={tab.label}
            onClick={() => handleTabChange(tab.value)}
            className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
              activeTab === tab.value
                ? "bg-blue-50 text-blue-700 font-medium"
                : "text-gray-600 hover:bg-gray-100"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {feedback.length === 0 ? (
        <p className="text-sm text-gray-500 py-8 text-center">
          No feedback {activeTab ? `with status "${activeTab}"` : "yet"}.
        </p>
      ) : (
        <div className="space-y-3">
          {feedback.map((item) => (
            <FeedbackCard
              key={item.id}
              item={item}
              onUpdateStatus={updateStatus}
            />
          ))}
        </div>
      )}
    </div>
  );
}
