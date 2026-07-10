import { lazy, Suspense } from "react";
import { NavLink, Route, Routes } from "react-router-dom";

const Dashboard = lazy(() => import("./pages/Dashboard").then(module => ({ default: module.Dashboard })));
const Runs = lazy(() => import("./pages/Runs").then(module => ({ default: module.Runs })));
const RunDetail = lazy(() => import("./pages/RunDetail").then(module => ({ default: module.RunDetail })));
const PromptComparison = lazy(() => import("./pages/PromptComparison").then(module => ({ default: module.PromptComparison })));
const RegressionCases = lazy(() => import("./pages/RegressionCases").then(module => ({ default: module.RegressionCases })));
const NotFound = lazy(() => import("./pages/NotFound").then(module => ({ default: module.NotFound })));

export default function App() {
  return <div className="app-shell"><aside><div className="brand"><span>AL</span><div><strong>Agent Lens <em>Alpha</em></strong><small>Workflow intelligence</small></div></div><nav><NavLink to="/" end>Overview</NavLink><NavLink to="/runs">Runs</NavLink><NavLink to="/prompts">Prompt comparison</NavLink><NavLink to="/regression">Regression cases</NavLink></nav><p className="aside-note">Make prompt changes measurable.<br />v0.1.0-alpha</p></aside><main><Suspense fallback={<div className="notice">Loading Agent Lens…</div>}><Routes><Route path="/" element={<Dashboard />} /><Route path="/runs" element={<Runs />} /><Route path="/runs/:id" element={<RunDetail />} /><Route path="/prompts" element={<PromptComparison />} /><Route path="/regression" element={<RegressionCases />} /><Route path="*" element={<NotFound />} /></Routes></Suspense></main></div>;
}
