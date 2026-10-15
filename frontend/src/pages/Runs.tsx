import { FormEvent, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import { RunsTable } from "../components/RunsTable";
import type { Run } from "../types";

export function Runs() {
  const [params, setParams] = useSearchParams();
  const query = params.get("q") ?? "";
  const offset = Math.max(0, Number(params.get("offset")) || 0);
  const [draft, setDraft] = useState(query);
  const [runs, setRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  useEffect(() => { setDraft(query); }, [query]);
  useEffect(() => {
    let active = true;
    setLoading(true); setError("");
    api.runs(offset, query).then(next => { if (active) setRuns(next); })
      .catch((e: Error) => { if (active) setError(e.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [query, offset, retry]);
  const search = (event: FormEvent) => { event.preventDefault(); setParams({ q: draft, offset: "0" }); };
  return <>
    <header className="page-head"><div><h1>All runs</h1><p>Search all stored runs by ID, workflow, source, prompt, or model.</p></div>
      <form onSubmit={search}><label>Search runs<input className="search" maxLength={200} value={draft} onChange={event => setDraft(event.target.value)} /></label><button className="button" type="submit">Search</button></form>
    </header>
    {loading ? <div className="notice" role="status">Loading runs…</div> : error ? <div className="notice error" role="alert">{error} <button className="button" onClick={() => setRetry(value => value + 1)}>Retry</button></div> : <>
      <section className="panel"><RunsTable runs={runs} />{!runs.length && query && <p>No matches for “{query}”. Change the search to try again.</p>}</section>
      <nav className="form-actions" aria-label="Run pages"><button className="button secondary" disabled={offset === 0} onClick={() => setParams({q: query, offset: String(Math.max(0, offset - 50))})}>Previous</button><span>Page {Math.floor(offset / 50) + 1} · {runs.length} runs</span><button className="button secondary" disabled={runs.length < 50} onClick={() => setParams({q: query, offset: String(offset + 50)})}>Next</button></nav>
    </>}
  </>;
}
