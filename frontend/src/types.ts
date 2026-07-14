export type Evaluation = {
  id: number;
  run_id: number;
  evaluator_type: string;
  evaluator_model: string;
  clarity_score: number;
  evidence_score: number;
  risk_coverage_score: number;
  specificity_score: number;
  actionability_score: number;
  novelty_score: number;
  overall_score: number;
  possible_hallucination: boolean;
  too_generic: boolean;
  missing_risks: boolean;
  overconfident_language: boolean;
  weak_evidence: boolean;
  needs_human_review: boolean;
  comments: string;
  created_at: string;
};

export type HumanReview = {
  id: number;
  run_id: number;
  evaluation_id: number;
  reviewer: string;
  review_decision: "pending" | "agree" | "adjust" | "reject";
  rubric_version: string;
  clarity_score: number;
  evidence_score: number;
  risk_coverage_score: number;
  specificity_score: number;
  actionability_score: number;
  novelty_score: number;
  overall_score: number;
  notes: string;
  scores_edited_after_reveal: boolean;
  created_at: string;
  updated_at: string;
};

export type HumanReviewDraft = Omit<
  HumanReview,
  "id" | "run_id" | "created_at" | "updated_at" | "scores_edited_after_reveal"
>;

export type Run = {
  id: number;
  workflow_name: string;
  source_type: string;
  input_text: string;
  output_text: string;
  prompt_version: string;
  model_name: string;
  provider: string;
  token_input: number;
  token_output: number;
  estimated_cost: number;
  latency_ms: number;
  status: string;
  error_message?: string;
  created_at: string;
  evaluations: Evaluation[];
};

export type CalibrationDimension = {
  dimension: string;
  sample_count: number;
  mae: number | null;
  rmse: number | null;
  bias: number | null;
  judge_mean: number | null;
  human_mean: number | null;
  agreement_rate: number | null;
  large_disagreement_rate: number | null;
  overrating_rate: number | null;
  underrating_rate: number | null;
  correlation: number | null;
};

export type CalibrationDisagreement = {
  run_id: number;
  evaluation_id: number;
  prompt_version: string;
  evaluator_model: string;
  judge_overall: number;
  human_overall: number;
  signed_delta: number;
  absolute_delta: number;
  decision: string;
  review_date: string;
  dangerous: boolean;
};

export type CalibrationSummary = {
  evaluator_model: string | null;
  rubric_version: string | null;
  review_count: number;
  calibrated_evaluation_count: number;
  reviewer_count: number;
  evaluated_evaluation_count: number;
  reviewed_evaluation_count: number;
  evaluation_coverage_rate: number | null;
  evaluated_run_count: number;
  reviewed_run_count: number;
  run_coverage_rate: number | null;
  overall_mae: number | null;
  overall_rmse: number | null;
  overall_bias: number | null;
  acceptance_rate: number | null;
  overall_agreement_rate: number | null;
  overall_large_disagreement_rate: number | null;
  overall_correlation: number | null;
  decision_counts: Record<string, number>;
  dimensions: CalibrationDimension[];
  disagreements: CalibrationDisagreement[];
  dangerous_samples: CalibrationDisagreement[];
};

export type CalibrationScope = {
  evaluator_model: string;
  rubric_version: string;
  review_count: number;
};

export type HumanReviewQueueItem = {
  run_id: number;
  evaluation_id: number;
  workflow_name: string;
  prompt_version: string;
  model_name: string;
  review_count: number;
  created_at: string;
};

export type Summary = {
  total_runs: number;
  average_overall_score: number | null;
  average_cost: number;
  average_latency_ms: number;
  failure_rate: number;
};

export type Trend = {
  day: string;
  run_count: number;
  average_cost: number;
  average_latency_ms: number;
  average_overall_score: number | null;
};

export type PromptComparison = {
  prompt_version: string;
  run_count: number;
  average_overall_score: number | null;
  average_clarity_score: number | null;
  average_evidence_score: number | null;
  average_risk_coverage_score: number | null;
  average_specificity_score: number | null;
  average_actionability_score: number | null;
  average_cost: number;
  average_latency_ms: number;
  failure_rate: number;
};

export type RegressionCase = {
  id: number;
  name: string;
  input_text: string;
  expected_focus: string;
  notes?: string;
  created_at: string;
};
