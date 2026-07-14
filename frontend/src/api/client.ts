import type {
  CalibrationScope,
  CalibrationSummary,
  HumanReview,
  HumanReviewDraft,
  HumanReviewQueueItem,
  PromptComparison,
  RegressionCase,
  Run,
  Summary,
  Trend,
} from "../types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init);
  if (!response.ok) {
    const body = await response.text();
    let message = body;
    try { message = JSON.parse(body).detail ?? body; } catch { /* keep plain-text response */ }
    throw new Error(message || `Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  summary: () => request<Summary>("/dashboard/summary"),
  trends: () => request<Trend[]>("/dashboard/trends"),
  promptComparison: () => request<PromptComparison[]>("/dashboard/prompt-comparison"),
  runs: () => request<Run[]>("/runs?limit=100"),
  run: (id: string) => request<Run>(`/runs/${id}`),
  humanReviews: (id: string | number) => request<HumanReview[]>(`/runs/${id}/human-reviews`),
  humanReviewQueue: () => request<HumanReviewQueueItem[]>("/human-review-queue?unreviewed=true&limit=100"),
  rankedRuns: () => request<{best: Run[]; worst: Run[]}>("/dashboard/ranked-runs"),
  calibrationScopes: () => request<CalibrationScope[]>("/dashboard/calibration/scopes"),
  calibration: (evaluatorModel?: string, rubricVersion?: string) => {
    const query = evaluatorModel && rubricVersion
      ? `?evaluator_model=${encodeURIComponent(evaluatorModel)}&rubric_version=${encodeURIComponent(rubricVersion)}`
      : "";
    return request<CalibrationSummary>(`/dashboard/calibration${query}`);
  },
  regressionCases: () => request<RegressionCase[]>("/regression-cases"),
  createRegressionCase: (payload: Pick<RegressionCase, "name" | "input_text" | "expected_focus" | "notes">) =>
    request<RegressionCase>("/regression-cases", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  evaluate: (id: number) => request(`/runs/${id}/evaluate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ evaluator_type: "mock" }),
  }),
  createHumanReview: (runId: number, payload: HumanReviewDraft) =>
    request<HumanReview>(`/runs/${runId}/human-reviews`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  updateHumanReview: (
    reviewId: number,
    payload: Omit<HumanReviewDraft, "evaluation_id">,
  ) => request<HumanReview>(`/human-reviews/${reviewId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  }),
};
