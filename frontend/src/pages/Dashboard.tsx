import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { RunsTable } from "../components/RunsTable";
import { ScoreCard } from "../components/ScoreCard";
import { TrendChart } from "../components/TrendChart";
import type { PromptComparison, Run, Summary, Trend } from "../types";

export function Dashboard() {
  const [data, setData] = useState<{summary: Summary; trends: Trend[]; runs: Run[]; prompts: PromptComparison[]; ranked: {best: Run[]; worst: Run[]}} | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { Promise.all([api.summary(), api.trends(), api.runs(), api.promptComparison(), api.rankedRuns()])
    .then(([summary, trends, runs, prompts, ranked]) => setData({ summary, trends, runs, prompts, ranked })).catch((e: Error) => setError(e.message)); }, []);
  if (error) return <div className="notice error">Could not load dashboard: {error}</div>;
  if (!data) return <div className="notice">Loading runs…</div>;
  const { summary, trends, runs, prompts, ranked } = data;
  return <>
    <header className="page-head"><div><p className="eyebrow">Overview</p><h1>Run summary</h1><p>Quality, cost, and latency for the runs stored in this workspace.</p></div><Link className="button" to="/runs">View runs</Link></header>
    <section className="score-grid">
      <ScoreCard label="Total runs" value={String(summary.total_runs)} hint="all workflows" />
      <ScoreCard label="Overall quality" value={summary.average_overall_score?.toFixed(2) ?? "—"} hint="out of 5" />
      <ScoreCard label="Average cost" value={`$${summary.average_cost.toFixed(4)}`} hint="per run" />
      <ScoreCard label="Average latency" value={`${Math.round(summary.average_latency_ms)} ms`} hint={`${(summary.failure_rate * 100).toFixed(1)}% failures`} />
    </section>
    <section className="trend-grid">
      <article className="panel chart"><div className="section-title"><div><p className="eyebrow">Quality</p><h2>Score trend</h2></div></div><TrendChart data={trends} field="average_overall_score" color="#0f766e" /></article>
      <article className="panel chart"><div className="section-title"><div><p className="eyebrow">Spend</p><h2>Cost trend</h2></div></div><TrendChart data={trends} field="average_cost" color="#6d5bd0" /></article>
      <article className="panel chart"><div className="section-title"><div><p className="eyebrow">Efficiency</p><h2>Latency trend</h2></div></div><TrendChart data={trends} field="average_latency_ms" color="#d97706" /></article>
    </section>
    <section className="panel"><div className="section-title"><div><p className="eyebrow">By version</p><h2>Prompt comparison</h2></div></div>
      <div className="table-wrap"><table><thead><tr><th>Version</th><th>Runs</th><th>Overall</th><th>Evidence</th><th>Risk</th><th>Cost</th><th>Failure</th></tr></thead><tbody>{prompts.map(p => <tr key={p.prompt_version}><td><span className="tag">{p.prompt_version}</span></td><td>{p.run_count}</td><td><strong>{p.average_overall_score?.toFixed(2) ?? "—"}</strong></td><td>{p.average_evidence_score?.toFixed(2) ?? "—"}</td><td>{p.average_risk_coverage_score?.toFixed(2) ?? "—"}</td><td>${p.average_cost.toFixed(4)}</td><td>{(p.failure_rate * 100).toFixed(1)}%</td></tr>)}</tbody></table></div>
    </section>
    <section className="panel"><div className="section-title"><div><p className="eyebrow">Latest activity</p><h2>Recent runs</h2></div><Link to="/runs">View all →</Link></div><RunsTable runs={runs.slice(0, 6)} compact /></section>
    <section className="dashboard-grid"><article className="panel"><div className="section-title"><div><p className="eyebrow">Highest scores</p><h2>Best runs</h2></div></div><RunsTable runs={ranked.best} compact /></article><article className="panel"><div className="section-title"><div><p className="eyebrow">Needs review</p><h2>Lowest scores</h2></div></div><RunsTable runs={ranked.worst} compact /></article></section>
  </>;
}
