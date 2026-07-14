import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { ScoreCard } from "../components/ScoreCard";
import type { CalibrationScope, CalibrationSummary } from "../types";

const dimensionLabels: Record<string, string> = {
  clarity_score: "Clarity",
  evidence_score: "Evidence",
  risk_coverage_score: "Risk coverage",
  specificity_score: "Specificity",
  actionability_score: "Actionability",
  novelty_score: "Novelty",
  overall_score: "Overall",
};

export function Calibration() {
  const [data, setData] = useState<CalibrationSummary | null>(null);
  const [scopes, setScopes] = useState<CalibrationScope[]>([]);
  const [scopeIndex, setScopeIndex] = useState(0);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = async (index = scopeIndex) => {
    setLoading(true); setError("");
    try {
      const available = scopes.length ? scopes : await api.calibrationScopes();
      setScopes(available);
      const scope = available[index];
      setData(await api.calibration(scope?.evaluator_model, scope?.rubric_version));
    }
    catch (caught) { setError((caught as Error).message); }
    finally { setLoading(false); }
  };

  useEffect(() => { void load(0); }, []);

  if (loading) return <div className="notice">Loading calibration…</div>;
  if (error) return <div className="notice error" role="alert"><p>Could not load calibration: {error}</p><button type="button" className="button" onClick={() => void load()}>Retry</button></div>;
  if (!data || !data.calibrated_evaluation_count) return <div className="notice"><h1>No paired reviews yet</h1><p>Save a blind human review to compare it with an exact evaluator result.</p><Link className="button" to="/review-queue">Open blind-review queue</Link></div>;

  return <>
    <header className="page-head"><div><p className="eyebrow">Calibration</p><h1>Human–model agreement</h1><p>Measure where evaluator scores align with, overrate, or underrate human judgments.</p></div><Link className="button" to="/review-queue">Review blind</Link></header>
    {scopes.length > 1 && <label className="scope-select">Calibration scope<select value={scopeIndex} onChange={event => { const next = Number(event.target.value); setScopeIndex(next); void load(next); }}>{scopes.map((scope, index) => <option key={`${scope.evaluator_model}:${scope.rubric_version}`} value={index}>{scope.evaluator_model} · {scope.rubric_version} ({scope.review_count})</option>)}</select></label>}
    <p className="muted">Scope: {data.evaluator_model} · {data.rubric_version}. Results never mix evaluator models or rubric versions.</p>
    <section className="score-grid">
      <ScoreCard label="Paired evaluations" value={String(data.calibrated_evaluation_count)} hint={`${data.review_count} human reviews`} />
      <ScoreCard label="Evaluation coverage" value={formatPercent(data.evaluation_coverage_rate)} hint={`${data.reviewed_evaluation_count} of ${data.evaluated_evaluation_count} evaluator results`} />
      <ScoreCard label="Overall MAE" value={formatMetric(data.overall_mae)} hint="lower is better" />
      <ScoreCard label="Agreement" value={formatPercent(data.overall_agreement_rate)} hint="absolute gap ≤ 0.5" />
    </section>
    {data.calibrated_evaluation_count < 5 && <div className="notice warning">Directional only — fewer than five paired evaluations.</div>}
    <section className="panel calibration-definitions">
      <h2>How to read this</h2>
      <p>A pair is one exact evaluator result and the consensus of its human reviews. Error is <code>model − human</code>. Positive bias means the model scores higher. MAE is the mean absolute error; agreement means an absolute gap of 0.5 or less. Model acceptance is reviewer-level: agree divided by agree + adjust + reject; pending reviews are excluded.</p>
      <div className="calibration-facts"><span>Bias <strong>{formatSigned(data.overall_bias)}</strong></span><span>Large disagreement <strong>{formatPercent(data.overall_large_disagreement_rate)}</strong></span><span>Correlation <strong>{formatMetric(data.overall_correlation)}</strong></span><span>Model accepted <strong>{formatPercent(data.acceptance_rate)}</strong></span></div>
    </section>
    <section className="panel">
      <div className="section-title"><div><p className="eyebrow">By dimension</p><h2>Calibration metrics</h2></div></div>
      <p className="table-hint">Scroll horizontally to see all columns.</p>
      <div className="table-wrap" role="region" aria-label="Calibration metrics by dimension" tabIndex={0}><table><thead><tr><th>Dimension</th><th>Pairs</th><th>Model mean</th><th>Human mean</th><th>Bias</th><th>MAE</th><th>Agreement</th></tr></thead><tbody>
        {data.dimensions.map(item => <tr key={item.dimension}><td>{dimensionLabels[item.dimension] ?? item.dimension}</td><td>{item.sample_count}</td><td>{formatMetric(item.judge_mean)}</td><td>{formatMetric(item.human_mean)}</td><td><span className={biasClass(item.bias)}>{formatSigned(item.bias)} · {biasText(item.bias)}</span></td><td>{formatMetric(item.mae)}</td><td>{formatPercent(item.agreement_rate)}</td></tr>)}
      </tbody></table></div>
    </section>
    <section className="panel">
      <div className="section-title"><div><p className="eyebrow">Review first</p><h2>Largest disagreements</h2></div><small>Sorted by absolute overall gap</small></div>
      <p className="table-hint">Scroll horizontally to see all columns.</p>
      {data.disagreements.length ? <div className="table-wrap" role="region" aria-label="Largest model and human disagreements" tabIndex={0}><table><thead><tr><th>Run</th><th>Prompt</th><th>Evaluator</th><th>Model</th><th>Human</th><th>Gap</th><th>Decision</th><th>Reviewed</th></tr></thead><tbody>
        {data.disagreements.map(item => <tr key={item.evaluation_id} className={item.dangerous ? "danger-row" : ""}><td><Link to={`/runs/${item.run_id}`}>#{item.run_id}{item.dangerous && <span className="danger-tag">High-risk</span>}</Link></td><td>{item.prompt_version}</td><td>{item.evaluator_model}</td><td>{item.judge_overall.toFixed(1)}</td><td>{item.human_overall.toFixed(1)}</td><td><span className={biasClass(item.signed_delta)}>{formatSigned(item.signed_delta)} · {biasText(item.signed_delta)}</span></td><td>{decisionLabel(item.decision)}</td><td>{new Date(item.review_date).toLocaleDateString()}</td></tr>)}
      </tbody></table></div> : <p className="muted">No disagreements to show.</p>}
    </section>
    {data.dangerous_samples.length > 0 && <section className="panel"><p className="eyebrow">Safety review</p><h2>High-risk overrating</h2><p>These cases have model score ≥ 4.0 and human consensus ≤ 2.5. They are listed independently so they cannot be hidden by the top-disagreement limit.</p><ul className="review-history">{data.dangerous_samples.map(item => <li key={item.evaluation_id}><Link to={`/runs/${item.run_id}`}>Run #{item.run_id} · evaluation #{item.evaluation_id}</Link><span>Model {item.judge_overall.toFixed(1)} · human {item.human_overall.toFixed(1)}</span></li>)}</ul></section>}
  </>;
}

function formatMetric(value: number | null): string { return value === null ? "—" : value.toFixed(2); }
function formatPercent(value: number | null): string { return value === null ? "—" : `${(value * 100).toFixed(1)}%`; }
function formatSigned(value: number | null): string { return value === null ? "—" : `${value >= 0 ? "+" : ""}${value.toFixed(2)}`; }
function biasClass(value: number | null): string { return value === null || Math.abs(value) < 0.005 ? "delta aligned" : value > 0 ? "delta higher" : "delta lower"; }
function biasText(value: number | null): string { return value === null ? "No data" : Math.abs(value) < 0.005 ? "Aligned" : value > 0 ? "Model higher" : "Model lower"; }
function decisionLabel(value: string): string { return { pending: "Pending", agree: "Accepted", adjust: "Adjusted", reject: "Rejected", mixed: "Mixed" }[value] ?? value; }
