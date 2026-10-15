import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type DateRange } from "../api/client";
import { RunsTable } from "../components/RunsTable";
import { ScoreCard } from "../components/ScoreCard";
import { TrendChart } from "../components/TrendChart";
import type { PromptComparison, Run, Summary, Trend } from "../types";

export function Dashboard() {
  const [range, setRange] = useState<DateRange>({});
  const [draft, setDraft] = useState({ date_from: "", date_to: "" });
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState("");
  const [data, setData] = useState<{summary: Summary; trends: Trend[]; runs: Run[]; prompts: PromptComparison[]; ranked: {best: Run[]; worst: Run[]}} | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    setError(""); setData(null);
    Promise.all([api.summary(range), api.trends(range), api.runs(0, "", range), api.promptComparison(range), api.rankedRuns(range)])
      .then(([summary, trends, runs, prompts, ranked]) => { if (active) setData({ summary, trends, runs, prompts, ranked }); })
      .catch((e: Error) => { if (active) setError(e.message); });
    return () => { active = false; };
  }, [range]);
  const apply = (event: FormEvent) => { event.preventDefault(); setRange(Object.fromEntries(Object.entries(draft).filter(([, value]) => value))); };
  const exportSummary = async () => {
    setExporting(true); setExportError("");
    try {
      const markdown = await api.exportReport(range);
      const url = URL.createObjectURL(new Blob([markdown], {type: "text/markdown;charset=utf-8"}));
      const link = document.createElement("a"); link.href = url; link.download = "evaluation-summary.md";
      link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (caught) { setExportError((caught as Error).message); }
    finally { setExporting(false); }
  };
  if (error) return <div className="notice error" role="alert">Could not load dashboard: {error} <button className="button" onClick={() => setRange({...range})}>Retry</button></div>;
  if (!data) return <div className="notice">Loading runs…</div>;
  const { summary, trends, runs, prompts, ranked } = data;
  return <>
    <header className="page-head"><div><p className="eyebrow">Overview</p><h1>Run summary</h1><p>Quality, cost, and latency for the runs stored in this workspace.</p></div><Link className="button" to="/runs">View runs</Link></header>
    <form className="form-actions date-filters" onSubmit={apply}>
      <label>From (UTC)<input type="date" value={draft.date_from} max={draft.date_to || undefined} onChange={event => setDraft({...draft, date_from: event.target.value})}/></label>
      <label>Through (UTC)<input type="date" value={draft.date_to} min={draft.date_from || undefined} onChange={event => setDraft({...draft, date_to: event.target.value})}/></label>
      <button className="button secondary" type="submit">Apply dates</button>
      <button className="button" type="button" disabled={exporting} onClick={() => void exportSummary()}>{exporting ? "Exporting…" : "Export displayed summary"}</button>
    </form>
    <p className="muted">Applied UTC range: {range.date_from || "beginning"} to {range.date_to || "present"}. Generation costs are caller-reported USD estimates; judge and retry overhead are excluded. Unknown values are omitted from averages.</p>
    {(summary.failed_evaluation_attempt_count > 0 || summary.pending_evaluation_attempt_count > 0) && <p className="notice warning">Judge attempts: {summary.failed_evaluation_attempt_count} failed, {summary.pending_evaluation_attempt_count} pending or interrupted. These attempts have no new score; inspect the run before retrying.</p>}
    {summary.legacy_usage_count > 0 && <p className="notice warning">{summary.legacy_usage_count} runs have unverified legacy measurements. Old zero values are excluded as unknown; nonzero historical estimates remain included.</p>}
    {exportError && <div className="notice error" role="alert">{exportError}</div>}
    <section className="score-grid">
      <ScoreCard label="Total runs" value={String(summary.total_runs)} hint="all workflows" />
      <ScoreCard label="Overall quality" value={summary.average_overall_score?.toFixed(2) ?? "—"} hint={`${summary.evaluated_count} evaluated runs · out of 5`} />
      <ScoreCard label="Average cost" value={summary.average_cost == null ? "Unknown" : `$${summary.average_cost.toFixed(4)}`} hint={`${summary.cost_sample_count} known-cost runs`} />
      <ScoreCard label="Average latency" value={summary.average_latency_ms == null ? "Unknown" : `${Math.round(summary.average_latency_ms)} ms`} hint={`${summary.latency_sample_count} timed runs · ${summary.failure_rate == null ? "unknown failure rate" : `${(summary.failure_rate * 100).toFixed(1)}% failures`}`} />
    </section>
    <section className="trend-grid">
      <article className="panel chart"><div className="section-title"><div><p className="eyebrow">Quality</p><h2>Score trend</h2></div></div><TrendChart data={trends} field="average_overall_score" color="#0f766e" /></article>
      <article className="panel chart"><div className="section-title"><div><p className="eyebrow">Spend</p><h2>Cost trend</h2></div></div><TrendChart data={trends} field="average_cost" color="#6d5bd0" /></article>
      <article className="panel chart"><div className="section-title"><div><p className="eyebrow">Efficiency</p><h2>Latency trend</h2></div></div><TrendChart data={trends} field="average_latency_ms" color="#d97706" /></article>
    </section>
    <section className="panel"><div className="section-title"><div><p className="eyebrow">By version</p><h2>Prompt comparison</h2></div></div>
      <div className="table-wrap"><table><thead><tr><th>Version</th><th>Runs</th><th>Overall</th><th>Evidence</th><th>Risk</th><th>Cost</th><th>Failure</th></tr></thead><tbody>{prompts.map(p => <tr key={p.prompt_version}><td><span className="tag">{p.prompt_version}</span></td><td>{p.run_count}</td><td><strong>{p.average_overall_score?.toFixed(2) ?? "—"}</strong></td><td>{p.average_evidence_score?.toFixed(2) ?? "—"}</td><td>{p.average_risk_coverage_score?.toFixed(2) ?? "—"}</td><td>{p.average_cost == null ? "Unknown" : `$${p.average_cost.toFixed(4)}`}</td><td>{p.failure_rate == null ? "—" : `${(p.failure_rate * 100).toFixed(1)}%`}</td></tr>)}</tbody></table></div>
    </section>
    <section className="panel"><div className="section-title"><div><p className="eyebrow">Latest activity</p><h2>Recent runs</h2></div><Link to="/runs">View all →</Link></div><RunsTable runs={runs.slice(0, 6)} compact /></section>
    <section className="dashboard-grid"><article className="panel"><div className="section-title"><div><p className="eyebrow">Highest scores</p><h2>Best runs</h2></div></div><RunsTable runs={ranked.best} compact /></article><article className="panel"><div className="section-title"><div><p className="eyebrow">Needs review</p><h2>Lowest scores</h2></div></div><RunsTable runs={ranked.worst} compact /></article></section>
  </>;
}
