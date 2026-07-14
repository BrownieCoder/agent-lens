import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import { EvaluationPanel } from "../components/EvaluationPanel";
import { HumanReviewPanel } from "../components/HumanReviewPanel";
import type { HumanReview, Run } from "../types";

export function RunDetail() {
  const { id = "" } = useParams();
  const [run, setRun] = useState<Run | null>(null);
  const [reviews, setReviews] = useState<HumanReview[]>([]);
  const [error, setError] = useState("");
  const [evaluating, setEvaluating] = useState(false);
  const [reviewDirty, setReviewDirty] = useState(false);

  const load = async () => {
    setError("");
    try {
      const [nextRun, nextReviews] = await Promise.all([api.run(id), api.humanReviews(id)]);
      setRun(nextRun); setReviews(nextReviews);
    } catch (caught) {
      setError((caught as Error).message);
    }
  };

  useEffect(() => { setReviewDirty(false); void load(); }, [id]);
  useEffect(() => {
    if (!reviewDirty) return;
    const beforeUnload = (event: BeforeUnloadEvent) => event.preventDefault();
    const protectInternalNavigation = (event: MouseEvent) => {
      const link = (event.target as Element | null)?.closest("a[href]");
      if (link && !window.confirm("Discard the unsaved human-review draft?")) {
        event.preventDefault(); event.stopImmediatePropagation();
      }
    };
    window.addEventListener("beforeunload", beforeUnload);
    document.addEventListener("click", protectInternalNavigation, true);
    return () => {
      window.removeEventListener("beforeunload", beforeUnload);
      document.removeEventListener("click", protectInternalNavigation, true);
    };
  }, [reviewDirty]);

  const evaluate = async () => {
    if (!run || reviewDirty) return;
    setEvaluating(true); setError("");
    try {
      await api.evaluate(run.id);
      await load();
    } catch (caught) {
      setError((caught as Error).message);
    } finally {
      setEvaluating(false);
    }
  };

  if (error && !run) return <div className="notice error" role="alert">{error}</div>;
  if (!run) return <div className="notice">Loading run…</div>;

  const evaluation = run.evaluations.at(-1);
  const currentReview = evaluation
    ? reviews.find(review => review.evaluation_id === evaluation.id && review.reviewer === "local-reviewer")
    : undefined;
  const previousReviews = reviews.filter(review => review.id !== currentReview?.id);

  return <>
    <Link className="back" to="/runs">← Back to runs</Link>
    <header className="page-head">
      <div><p className="eyebrow">{run.workflow_name} · {run.source_type}</p><h1>Run #{run.id}</h1><p>{new Date(run.created_at).toLocaleString()} · {run.prompt_version} · {run.model_name}</p></div>
      <button type="button" className="button" onClick={evaluate} disabled={evaluating || reviewDirty} aria-describedby={reviewDirty ? "review-draft-warning" : undefined}>{evaluating ? "Evaluating…" : "Run mock evaluation"}</button>
    </header>
    {error && <div className="notice error" role="alert">{error}</div>}
    <section className="meta-grid"><Score label="Cost" value={`$${run.estimated_cost.toFixed(4)}`} /><Score label="Latency" value={`${run.latency_ms} ms`} /><Score label="Tokens" value={`${run.token_input + run.token_output}`} /><Score label="Status" value={run.status} /></section>
    <section className="text-grid"><article className="panel"><p className="eyebrow">Input</p><h2>Source material</h2><pre>{run.input_text}</pre></article><article className="panel"><p className="eyebrow">Output</p><h2>Generated report</h2><pre>{run.output_text || run.error_message || "No output"}</pre></article></section>
    {reviewDirty && <div id="review-draft-warning" className="notice warning">Save or cancel the human-review draft before rerunning the evaluator or leaving this page.</div>}
    <HumanReviewPanel key={evaluation?.id ?? "no-evaluation"} runId={run.id} evaluation={evaluation} existingReview={currentReview} onSaved={load} onDirtyChange={setReviewDirty} />
    {evaluation && currentReview ? <EvaluationPanel evaluation={evaluation} /> : evaluation ? <div className="notice">Model scores are hidden until blind human scores are saved.</div> : <div className="notice">This run has not been evaluated.</div>}
    {!currentReview && previousReviews.length > 0 && <div className="notice">{previousReviews.length} prior review{previousReviews.length === 1 ? " is" : "s are"} retained. Details stay hidden until this blind score is saved.</div>}
    {currentReview && previousReviews.length > 0 && <section className="panel"><p className="eyebrow">Review history</p><h2>Other and previous reviews</h2><p className="muted">Rerunning never overwrites reviews; each reviewer entry remains bound to its original evaluation.</p><ul className="review-history">{previousReviews.map(review => <li key={review.id}><strong>Evaluation #{review.evaluation_id} · {review.reviewer}</strong><span>{decisionLabel(review.review_decision)} · {new Date(review.updated_at).toLocaleString()}</span></li>)}</ul></section>}
  </>;
}

function decisionLabel(value: HumanReview["review_decision"]): string {
  return { pending: "Decision pending", agree: "Model accepted", adjust: "Adjusted", reject: "Rejected" }[value];
}

function Score({ label, value }: { label: string; value: string }) {
  return <div><span>{label}</span><strong>{value}</strong></div>;
}
