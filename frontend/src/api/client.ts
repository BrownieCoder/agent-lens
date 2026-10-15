import type {
  BlindRun,
  Evaluation,
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
    try {
      const detail = JSON.parse(body).detail;
      message = typeof detail === "string" ? detail : Array.isArray(detail)
        ? detail.map((item: { loc?: string[]; msg?: string }) => `${item.loc?.join(".") ?? "Input"}: ${item.msg ?? "Invalid value"}`).join("; ")
        : `Request failed: ${response.status}`;
    } catch { /* keep plain-text response */ }
    throw new Error(message || `Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export type DateRange = { date_from?: string; date_to?: string };
function dateQuery(range: DateRange = {}): string {
  const query = new URLSearchParams(Object.entries(range).filter(([, value]) => !!value));
  return query.size ? `?${query}` : "";
}

export const api = {
  exportReport: async (range: DateRange = {}) => {
    const response = await fetch(`${API_BASE}/reports/evaluation-summary`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(range),
    });
    if (!response.ok) throw new Error(`Report export failed (${response.status}). Check the selected dates and retry.`);
    return response.text();
  },
  summary: (range?: DateRange) => request<Summary>(`/dashboard/summary${dateQuery(range)}`),
  trends: (range?: DateRange) => request<Trend[]>(`/dashboard/trends${dateQuery(range)}`),
  promptComparison: (range?: DateRange) => request<PromptComparison[]>(`/dashboard/prompt-comparison${dateQuery(range)}`),
  runs: (offset = 0, q = "", range: DateRange = {}) => request<Run[]>(`/runs?${new URLSearchParams({limit: "50", offset: String(offset), q, ...range})}`),
  blindRun: (id: string, evaluationId?: string) => request<BlindRun>(`/runs/${id}/blind${evaluationId ? `?evaluation_id=${encodeURIComponent(evaluationId)}` : ""}`),
  run: (id: string) => request<Run>(`/runs/${id}`),
  humanReviews: (id: string | number) => request<HumanReview[]>(`/runs/${id}/human-reviews`),
  humanReviewQueue: (offset = 0) => request<HumanReviewQueueItem[]>(`/human-review-queue?unreviewed=true&limit=50&offset=${offset}`),
  rankedRuns: (range?: DateRange) => request<{best: Run[]; worst: Run[]}>(`/dashboard/ranked-runs${dateQuery(range)}`),
  calibrationScopes: () => request<CalibrationScope[]>("/dashboard/calibration/scopes"),
  calibration: (evaluatorModel?: string, rubricVersion?: string, judgeRubricVersion?: string) => {
    const query = evaluatorModel && rubricVersion
      ? `?evaluator_model=${encodeURIComponent(evaluatorModel)}&rubric_version=${encodeURIComponent(rubricVersion)}&judge_rubric_version=${encodeURIComponent(judgeRubricVersion ?? "research-report-v1")}`
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
  evaluate: (id: number) => request<Evaluation>(`/runs/${id}/evaluate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ evaluator_type: "mock", request_id: crypto.randomUUID() }),
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
