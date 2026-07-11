import { FormEvent, useEffect, useState } from "react";
import { api } from "../api/client";
import type { RegressionCase } from "../types";

const emptyForm = { name: "", input_text: "", expected_focus: "", notes: "" };

export function RegressionCases() {
  const [cases, setCases] = useState<RegressionCase[]>([]);
  const [form, setForm] = useState(emptyForm);
  const [error, setError] = useState("");
  const load = () => api.regressionCases().then(setCases).catch((e: Error) => setError(e.message));
  useEffect(() => { void load(); }, []);
  const submit = async (event: FormEvent) => {
    event.preventDefault(); setError("");
    try { await api.createRegressionCase(form); setForm(emptyForm); await load(); }
    catch (e) { setError((e as Error).message); }
  };
  return <>
    <header className="page-head"><div><p className="eyebrow">Test set</p><h1>Regression cases</h1><p>Keep inputs that should be rerun after a prompt or model change.</p></div></header>
    <section className="regression-grid">
      <form className="panel case-form" onSubmit={submit}><h2>Add a case</h2>
        <label>Name<input required value={form.name} onChange={e=>setForm({...form,name:e.target.value})} /></label>
        <label>Input text<textarea required rows={6} value={form.input_text} onChange={e=>setForm({...form,input_text:e.target.value})} /></label>
        <label>Expected focus<textarea required rows={3} value={form.expected_focus} onChange={e=>setForm({...form,expected_focus:e.target.value})} /></label>
        <label>Notes<input value={form.notes} onChange={e=>setForm({...form,notes:e.target.value})} /></label>
        <button className="button">Create regression case</button>{error && <p className="form-error">{error}</p>}
      </form>
      <div>{cases.map(item=><article className="panel case" key={item.id}><p className="eyebrow">Case #{item.id}</p><h2>{item.name}</h2><p>{item.input_text}</p><strong>Expected focus</strong><p>{item.expected_focus}</p>{item.notes && <small>{item.notes}</small>}</article>)}{!cases.length && <div className="notice">No regression cases yet.</div>}</div>
    </section>
  </>;
}
