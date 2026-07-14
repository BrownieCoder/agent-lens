import { FormEvent, useMemo, useRef, useState } from "react";
import { api } from "../api/client";
import type { Evaluation, HumanReview, HumanReviewDraft } from "../types";

const scoreFields = [
  ["clarity_score", "Clarity"], ["evidence_score", "Evidence"],
  ["risk_coverage_score", "Risk coverage"], ["specificity_score", "Specificity"],
  ["actionability_score", "Actionability"], ["novelty_score", "Novelty"],
  ["overall_score", "Overall"],
] as const;
type ScoreKey = (typeof scoreFields)[number][0];
type EditableDraft = Omit<HumanReviewDraft, ScoreKey> & Record<ScoreKey, number | null>;

function emptyDraft(evaluationId: number): EditableDraft {
  return {
    evaluation_id: evaluationId, reviewer: "local-reviewer", review_decision: "pending",
    rubric_version: "research-report-v1", clarity_score: null, evidence_score: null,
    risk_coverage_score: null, specificity_score: null, actionability_score: null,
    novelty_score: null, overall_score: null, notes: "",
  };
}

function reviewDraft(review: HumanReview): EditableDraft {
  const { id: _id, run_id: _runId, created_at: _createdAt, updated_at: _updatedAt,
    scores_edited_after_reveal: _edited, ...draft } = review;
  return draft;
}

export function HumanReviewPanel({ runId, evaluation, existingReview, onSaved, onDirtyChange }: {
  runId: number; evaluation?: Evaluation; existingReview?: HumanReview;
  onSaved: () => Promise<void>; onDirtyChange: (dirty: boolean) => void;
}) {
  const [review, setReview] = useState(existingReview);
  const [draft, setDraft] = useState<EditableDraft>(existingReview ? reviewDraft(existingReview) : emptyDraft(evaluation?.id ?? 0));
  const [editing, setEditing] = useState(!existingReview);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const firstMissing = useRef<HTMLFieldSetElement>(null);
  const decisionRef = useRef<HTMLSelectElement>(null);
  const notesRef = useRef<HTMLTextAreaElement>(null);
  const modelScores = useMemo(() => new Map<ScoreKey, number>(
    evaluation ? scoreFields.map(([key]) => [key, evaluation[key]]) : [],
  ), [evaluation]);

  const change = (values: Partial<EditableDraft>) => {
    setDraft(current => ({ ...current, ...values }));
    onDirtyChange(true); setMessage("");
  };

  if (!evaluation) return <section className="panel"><p className="eyebrow">Human review</p><h2>Evaluate this run first</h2><p className="muted">A human review binds to one exact evaluator result.</p></section>;

  const completeDraft = (): HumanReviewDraft | null => {
    if (scoreFields.some(([key]) => draft[key] === null)) {
      setError("Rate every dimension before saving.");
      requestAnimationFrame(() => firstMissing.current?.focus());
      return null;
    }
    return draft as HumanReviewDraft;
  };

  const saveScores = async (event: FormEvent) => {
    event.preventDefault(); setError(""); setMessage("");
    const payload = completeDraft(); if (!payload) return;
    setSaving(true);
    try {
      const changed = !!review && scoreFields.some(([key]) => review[key] !== payload[key]);
      const next = changed ? { ...payload, review_decision: "pending" as const } : payload;
      const saved = review
        ? await api.updateHumanReview(review.id, withoutEvaluationId(next))
        : await api.createHumanReview(runId, { ...next, evaluation_id: evaluation.id, review_decision: "pending" });
      setReview(saved); setDraft(reviewDraft(saved)); setEditing(false); onDirtyChange(false);
      setMessage(changed ? "Scores updated. Choose a new decision." : "Blind scores saved. Model scores are now revealed.");
      await onSaved();
    } catch (caught) { setError((caught as Error).message); }
    finally { setSaving(false); }
  };

  const saveDecision = async (event: FormEvent) => {
    event.preventDefault(); if (!review) return;
    if (draft.review_decision === "pending") {
      setError("Choose a review decision before saving."); decisionRef.current?.focus(); return;
    }
    if ((draft.review_decision === "adjust" || draft.review_decision === "reject") && !draft.notes.trim()) {
      setError("Explain why the model assessment was adjusted or rejected."); notesRef.current?.focus(); return;
    }
    const payload = completeDraft(); if (!payload) return;
    setSaving(true); setError("");
    try {
      const saved = await api.updateHumanReview(review.id, withoutEvaluationId(payload));
      setReview(saved); setDraft(reviewDraft(saved)); onDirtyChange(false); setMessage("Review decision saved.");
      await onSaved();
    } catch (caught) { setError((caught as Error).message); }
    finally { setSaving(false); }
  };

  return <section className="panel human-review-panel">
    <div className="section-title"><div><p className="eyebrow">Human review</p><h2>{review ? "Human–model comparison" : "Blind quality review"}</h2></div>{review && !editing && <span className={`review-state ${review.review_decision}`}>{decisionLabel(review.review_decision)}</span>}</div>
    <p className="muted">Bound to evaluation #{evaluation.id} · {evaluation.evaluator_model} · {new Date(evaluation.created_at).toLocaleString()}</p>
    {editing ? <form onSubmit={saveScores} className="review-form">
      {!review && <div className="blind-note">Model scores stay hidden until every human rating is actively selected and saved.</div>}
      {review && <div className="blind-note">Changing a score resets the decision to pending and records that the edit happened after reveal.</div>}
      <div className="rating-grid">{scoreFields.map(([key, label]) => {
        const missing = draft[key] === null;
        return <fieldset key={key} ref={missing && !scoreFields.slice(0, scoreFields.findIndex(([item]) => item === key)).some(([item]) => draft[item] === null) ? firstMissing : undefined} tabIndex={missing ? -1 : undefined}>
          <legend>{label}{key === "overall_score" && <small> independent judgment</small>}</legend>
          <div className="radio-row">{[1,2,3,4,5].map(value => <label key={value}><input type="radio" name={key} value={value} checked={draft[key] === value} onChange={() => change({ [key]: value })}/><span>{value}</span></label>)}</div><small>1 poor · 3 adequate · 5 strong</small>
        </fieldset>;
      })}</div>
      <label className="notes-field">Review notes<textarea rows={3} maxLength={4000} value={draft.notes} onChange={event => change({ notes: event.target.value })}/></label>
      <div className="form-actions">{review && <button type="button" className="button secondary" onClick={() => { setDraft(reviewDraft(review)); setEditing(false); setError(""); onDirtyChange(false); }}>Cancel</button>}<button type="submit" className="button" disabled={saving}>{saving ? "Saving…" : review ? "Save changes" : "Save blind scores"}</button></div>
    </form> : review ? <>
      <div className="table-wrap human-model-table" role="region" aria-labelledby="comparison-heading" tabIndex={0}><table><caption id="comparison-heading">Human and model score comparison</caption><thead><tr><th>Dimension</th><th>Human</th><th>Model</th><th>Model − human</th></tr></thead><tbody>{scoreFields.map(([key,label]) => { const delta=(modelScores.get(key)??0)-review[key]; return <tr key={key}><td>{label}</td><td>{review[key].toFixed(1)}</td><td>{(modelScores.get(key)??0).toFixed(1)}</td><td><span className={deltaClass(delta)}>{formatDelta(delta)} · {deltaText(delta)}</span></td></tr>; })}</tbody></table></div>
      <form onSubmit={saveDecision} className="decision-form">
        <label>Decision<select ref={decisionRef} value={draft.review_decision} aria-invalid={draft.review_decision === "pending" && !!error} onChange={event => change({ review_decision: event.target.value as HumanReviewDraft["review_decision"] })}><option value="pending">Choose a decision…</option><option value="agree">Accept model assessment</option><option value="adjust">Keep human adjustment</option><option value="reject">Reject model assessment</option></select></label>
        <label className="notes-field">Notes<textarea ref={notesRef} rows={3} maxLength={4000} value={draft.notes} onChange={event => change({ notes: event.target.value })}/></label>
        <div className="form-actions"><button type="button" className="button secondary" onClick={() => { setEditing(true); onDirtyChange(false); }}>Edit scores</button><button type="submit" className="button" disabled={saving}>{saving ? "Saving…" : "Save decision"}</button></div>
      </form>
      {review.scores_edited_after_reveal && <p className="muted">Score provenance: edited after model scores were revealed.</p>}
      <small>Rubric: {review.rubric_version} · updated {new Date(review.updated_at).toLocaleString()}</small>
    </> : null}
    {error && <p className="form-error" role="alert">{error}</p>}<p className="form-success" aria-live="polite">{message}</p>
  </section>;
}

function withoutEvaluationId(draft: HumanReviewDraft): Omit<HumanReviewDraft, "evaluation_id"> { const { evaluation_id: _id, ...payload } = draft; return payload; }
function decisionLabel(value: HumanReview["review_decision"]): string { return { pending:"Decision pending",agree:"Model accepted",adjust:"Adjusted",reject:"Rejected" }[value]; }
function formatDelta(value:number):string{return `${value>=0?"+":""}${value.toFixed(1)}`;}
function deltaText(value:number):string{return Math.abs(value)<.05?"Aligned":value>0?"Model higher":"Model lower";}
function deltaClass(value:number):string{return Math.abs(value)<.05?"delta aligned":value>0?"delta higher":"delta lower";}
