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
