import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { PromptComparison as Comparison } from "../types";

const dimensions: [keyof Comparison, string][] = [
  ["average_clarity_score", "Clarity"], ["average_evidence_score", "Evidence"],
  ["average_risk_coverage_score", "Risk coverage"], ["average_specificity_score", "Specificity"],
  ["average_actionability_score", "Actionability"], ["average_overall_score", "Overall"],
];

export function PromptComparison() {
  const [rows, setRows] = useState<Comparison[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  useEffect(() => { api.promptComparison().then(setRows).catch((e: Error) => setError(e.message)).finally(() => setLoading(false)); }, []);
  return <>
    <header className="page-head"><div><p className="eyebrow">Versions</p><h1>Prompt comparison</h1><p>Compare average scores, cost, latency, and failures by prompt version.</p></div></header>
    <p className="notice">Observational cohorts, not a causal improvement estimate. Scores use each run’s latest evaluation; retries are separate runs. Check matched inputs and generation/judge models before comparing.</p>
    {loading ? <div className="notice" role="status">Loading prompt comparisons…</div> : error ? <div className="notice error">{error}</div> : <section className="comparison-cards">{rows.map((row) => <article className="panel" key={row.prompt_version}>
      <div className="section-title"><div><h2>{row.prompt_version}</h2></div><strong className="overall">{row.average_overall_score?.toFixed(2) ?? "—"}</strong></div>
      <div className="dimension-grid">{dimensions.map(([key,label]) => <div key={key}><span>{label}</span><strong>{typeof row[key] === "number" ? Number(row[key]).toFixed(2) : "—"}</strong></div>)}</div>
      <p>{row.evaluated_count} evaluated / {row.run_count} runs · {row.matched_input_count} matched inputs · {row.unpaired_input_count} unpaired · {row.duplicate_input_count} repeat runs</p>
      <p className="muted">Workflows: {row.workflows?.join(", ")}. Generation models: {row.models?.join(", ")}. Judges: {row.evaluator_models?.join(", ") || "none"}.</p>
      <p className="muted">Missing reproducibility metadata: {row.missing_provenance_count} runs. Legacy usage: {row.legacy_usage_count}. Datasets: {row.datasets?.join(", ") || "not recorded"}; experiments: {row.experiments?.join(", ") || "not recorded"}.</p>
      <footer>{row.average_cost == null ? "Unknown cost" : `$${row.average_cost.toFixed(4)} USD`} ({row.cost_sample_count} known) · {row.average_latency_ms == null ? "Unknown latency" : `${Math.round(row.average_latency_ms)} ms`} ({row.latency_sample_count} timed) · {row.failure_rate == null ? "—" : `${(row.failure_rate*100).toFixed(1)}%`} failed</footer>
    </article>)}{!rows.length && <div className="notice">No runs to compare. Record runs through POST /runs to get started.</div>}</section>}
  </>;
}
