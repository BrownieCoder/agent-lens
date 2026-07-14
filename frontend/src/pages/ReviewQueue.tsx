import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { HumanReviewQueueItem } from "../types";

export function ReviewQueue() {
  const [items, setItems] = useState<HumanReviewQueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = async () => {
    setLoading(true); setError("");
    try { setItems(await api.humanReviewQueue()); }
    catch (caught) { setError((caught as Error).message); }
    finally { setLoading(false); }
  };
  useEffect(() => { void load(); }, []);

  if (loading) return <div className="notice">Loading blind-review queue…</div>;
  if (error) return <div className="notice error" role="alert"><p>Could not load the review queue: {error}</p><button className="button" type="button" onClick={() => void load()}>Retry</button></div>;

  return <>
    <header className="page-head"><div><p className="eyebrow">Blind review</p><h1>Unreviewed evaluator results</h1><p>This queue deliberately hides evaluator scores, flags, and rankings to reduce anchoring.</p></div></header>
    <div className="notice warning">Start human judgment here. Analytics and Runs pages contain model scores and are not blind-review entry points.</div>
    <section className="panel"><div className="section-title"><div><h2>Review queue</h2><p className="muted">Newest runs first, without model-priority sorting.</p></div><small>{items.length} waiting</small></div>
      {items.length ? <div className="table-wrap" role="region" aria-label="Unreviewed evaluations" tabIndex={0}><table><thead><tr><th>Run</th><th>Workflow</th><th>Prompt</th><th>Generation model</th><th>Created</th><th></th></tr></thead><tbody>{items.map(item => <tr key={item.evaluation_id}><td>#{item.run_id}</td><td>{item.workflow_name}</td><td>{item.prompt_version}</td><td>{item.model_name}</td><td>{new Date(item.created_at).toLocaleString()}</td><td><Link className="button compact-button" to={`/runs/${item.run_id}`}>Review blind</Link></td></tr>)}</tbody></table></div> : <div className="empty"><h2>Queue clear</h2><p>Every latest evaluator result has at least one human review.</p></div>}
    </section>
  </>;
}
