import type { Evaluation } from "../types";

const scoreKeys: [keyof Evaluation, string][] = [
  ["clarity_score", "Clarity"], ["evidence_score", "Evidence"], ["risk_coverage_score", "Risk coverage"],
  ["specificity_score", "Specificity"], ["actionability_score", "Actionability"], ["novelty_score", "Novelty"],
];
const flagKeys: [keyof Evaluation, string][] = [
  ["possible_hallucination", "Possible hallucination"], ["too_generic", "Too generic"],
  ["missing_risks", "Missing risks"], ["overconfident_language", "Overconfident"],
  ["weak_evidence", "Weak evidence"], ["needs_human_review", "Human review"],
];

export function EvaluationPanel({ evaluation }: { evaluation: Evaluation }) {
  return (
    <section className="panel evaluation-panel">
      <div className="section-title"><div><p className="eyebrow">Evaluation</p><h2>Quality breakdown</h2></div><strong className="overall">{evaluation.overall_score.toFixed(1)}<small>/ 5</small></strong></div>
      <div className="score-list">{scoreKeys.map(([key, label]) => <div key={key}><span>{label}</span><div className="bar"><i style={{ width: `${Number(evaluation[key]) * 20}%` }} /></div><b>{Number(evaluation[key]).toFixed(1)}</b></div>)}</div>
      <div className="flags">{flagKeys.filter(([key]) => evaluation[key]).map(([key, label]) => <span key={key}>{label}</span>)}{!flagKeys.some(([key]) => evaluation[key]) && <em>No flags raised</em>}</div>
      <p className="comments">{evaluation.comments}</p>
      <small>{evaluation.evaluator_type} · {evaluation.evaluator_model}</small>
    </section>
  );
}
