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
  const [error, setError] = useState("");
  useEffect(() => { api.promptComparison().then(setRows).catch((e: Error) => setError(e.message)); }, []);
  return <>
    <header className="page-head"><div><p className="eyebrow">Experiment readout</p><h1>Prompt comparison</h1><p>Judge quality gains against cost, latency, and reliability.</p></div></header>
    {error ? <div className="notice error">{error}</div> : <section className="comparison-cards">{rows.map((row, index) => <article className="panel" key={row.prompt_version}>
      <div className="section-title"><div><p className="eyebrow">{index === 0 ? "Current leader" : "Version"}</p><h2>{row.prompt_version}</h2></div><strong className="overall">{row.average_overall_score?.toFixed(2) ?? "—"}</strong></div>
      <div className="dimension-grid">{dimensions.map(([key,label]) => <div key={key}><span>{label}</span><strong>{typeof row[key] === "number" ? Number(row[key]).toFixed(2) : "—"}</strong></div>)}</div>
      <footer>{row.run_count} runs · ${row.average_cost.toFixed(4)} avg · {Math.round(row.average_latency_ms)} ms · {(row.failure_rate*100).toFixed(1)}% failed</footer>
    </article>)}</section>}
  </>;
}
