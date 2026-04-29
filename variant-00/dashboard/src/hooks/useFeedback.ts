import { useState, useEffect, useCallback, useRef } from "react";
import { api } from "../lib/api";

export interface FeedbackItem {
  id: string;
  skill_id: string;
  skill_name: string | null;
  feedback_text: string;
  status: string;
  created_at: string;
  team_id?: string;
  submitter_team_name?: string;
}

export function useFeedback() {
  const [feedback, setFeedback] = useState<FeedbackItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchFeedback = useCallback(async (status?: string) => {
    try {
      setError(null);
      const params = new URLSearchParams({ include_submitter: "true" });
      if (status) params.set("status", status);
      const data = await api.get<{ feedback: FeedbackItem[] }>(
        `/api/v1/feedback?${params.toString()}`
      );
      setFeedback(data.feedback);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load feedback");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchFeedback();
  }, [fetchFeedback]);

  const feedbackRef = useRef(feedback);
  feedbackRef.current = feedback;

  const updateStatus = useCallback(
    async (feedbackId: string, status: "reviewed" | "applied") => {
      const previous = feedbackRef.current;
      setFeedback((prev) =>
        prev.map((f) => (f.id === feedbackId ? { ...f, status } : f))
      );
      try {
        await api.patch(`/api/v1/feedback/${feedbackId}`, { status });
      } catch (e) {
        setFeedback(previous);
        throw e;
      }
    },
    []
  );

  return { feedback, loading, error, refresh: fetchFeedback, updateStatus };
}
