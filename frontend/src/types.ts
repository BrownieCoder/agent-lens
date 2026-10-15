export type Evaluation = {
  id: number;
  run_id: number;
  evaluator_type: string;
  evaluator_model: string;
  rubric_version: string;
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
  original_scores: Record<string, number> | null;
  created_at: string;
  updated_at: string;
};

export type HumanReviewDraft = Omit<
  HumanReview,
  "id" | "run_id" | "created_at" | "updated_at" | "scores_edited_after_reveal" | "original_scores"
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
  token_input: number | null;
  token_output: number | null;
  estimated_cost: number | null;
  latency_ms: number | null;
  status: string;
  error_message?: string;
  last_evaluation_error?: string | null;
  usage_source?: string;
  legacy_usage?: Record<string, number> | null;
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
  judge_rubric_version: string;
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
  judge_rubric_version: string;
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
  evaluated_count: number;
  failed_evaluation_attempt_count: number;
  pending_evaluation_attempt_count: number;
  legacy_usage_count: number;
  cost_sample_count: number;
  latency_sample_count: number;
  average_overall_score: number | null;
  average_cost: number | null;
  average_latency_ms: number | null;
  failure_rate: number | null;
};

export type Trend = {
  day: string;
  run_count: number;
  average_cost: number | null;
  average_latency_ms: number | null;
  average_overall_score: number | null;
};

export type PromptComparison = {
  prompt_version: string;
  run_count: number;
  legacy_usage_count: number;
  missing_provenance_count: number;
  datasets: string[];
  experiments: string[];
  evaluated_count: number;
  matched_input_count: number;
  unpaired_input_count: number;
  duplicate_input_count: number;
  workflows: string[];
  models: string[];
  evaluator_models: string[];
  cost_sample_count: number;
  latency_sample_count: number;
  average_overall_score: number | null;
  average_clarity_score: number | null;
  average_evidence_score: number | null;
  average_risk_coverage_score: number | null;
  average_specificity_score: number | null;
  average_actionability_score: number | null;
  average_cost: number | null;
  average_latency_ms: number | null;
  failure_rate: number | null;
};

export type RegressionCase = {
  id: number;
  name: string;
  input_text: string;
  expected_focus: string;
  notes?: string;
  created_at: string;
};

export type ReviewEvaluation = Pick<Evaluation, "id" | "run_id" | "evaluator_type" | "evaluator_model" | "created_at"> & Partial<Evaluation>;
export type BlindRun = { run: Run; evaluation: ReviewEvaluation | null; review: HumanReview | null };
