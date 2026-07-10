import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import { RunsTable } from "../components/RunsTable";
import type { Run } from "../types";

export function Runs() {
  const [runs, setRuns] = useState<Run[]>([]); const [query, setQuery] = useState(""); const [error, setError] = useState("");
  useEffect(() => { api.runs().then(setRuns).catch((e: Error) => setError(e.message)); }, []);
  const filtered = useMemo(() => runs.filter(run => `${run.id} ${run.workflow_name} ${run.source_type} ${run.prompt_version} ${run.model_name}`.toLowerCase().includes(query.toLowerCase())), [runs, query]);
  return <><header className="page-head"><div><p className="eyebrow">Run explorer</p><h1>All workflow runs</h1><p>Inspect output quality and diagnose weak runs.</p></div><input className="search" placeholder="Filter runs…" value={query} onChange={e => setQuery(e.target.value)} /></header>{error ? <div className="notice error">{error}</div> : <section className="panel"><RunsTable runs={filtered} /></section>}</>;
}
