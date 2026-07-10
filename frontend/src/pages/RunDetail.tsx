import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import { EvaluationPanel } from "../components/EvaluationPanel";
import type { Run } from "../types";

export function RunDetail() {
  const { id = "" } = useParams(); const [run, setRun] = useState<Run | null>(null); const [error, setError] = useState(""); const [evaluating, setEvaluating] = useState(false);
  const load = () => api.run(id).then(setRun).catch((e: Error) => setError(e.message));
  useEffect(() => { void load(); }, [id]);
  const evaluate = async () => { if (!run) return; setEvaluating(true); await api.evaluate(run.id); await load(); setEvaluating(false); };
  if (error) return <div className="notice error">{error}</div>; if (!run) return <div className="notice">Loading run…</div>;
  const evaluation = run.evaluations.at(-1);
  return <><Link className="back" to="/runs">← Back to runs</Link><header className="page-head"><div><p className="eyebrow">{run.workflow_name} · {run.source_type}</p><h1>Run #{run.id}</h1><p>{new Date(run.created_at).toLocaleString()} · {run.prompt_version} · {run.model_name}</p></div><button className="button" onClick={evaluate} disabled={evaluating}>{evaluating ? "Evaluating…" : "Run mock evaluation"}</button></header>
    <section className="meta-grid"><Score label="Cost" value={`$${run.estimated_cost.toFixed(4)}`} /><Score label="Latency" value={`${run.latency_ms} ms`} /><Score label="Tokens" value={`${run.token_input + run.token_output}`} /><Score label="Status" value={run.status} /></section>
    {evaluation ? <EvaluationPanel evaluation={evaluation} /> : <div className="notice">This run has not been evaluated.</div>}
    <section className="text-grid"><article className="panel"><p className="eyebrow">Input</p><h2>Source material</h2><pre>{run.input_text}</pre></article><article className="panel"><p className="eyebrow">Output</p><h2>Generated report</h2><pre>{run.output_text || run.error_message || "No output"}</pre></article></section>
  </>;
}
function Score({label, value}: {label: string; value: string}) { return <div><span>{label}</span><strong>{value}</strong></div>; }
