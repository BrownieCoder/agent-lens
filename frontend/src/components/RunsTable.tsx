import { Link } from "react-router-dom";
import type { Run } from "../types";

export function RunsTable({ runs, compact = false }: { runs: Run[]; compact?: boolean }) {
  return (
    <div className="table-wrap">
      <table>
        <thead><tr><th>Run</th><th>Prompt</th><th>Model</th><th>Score</th>{!compact && <><th>Cost</th><th>Latency</th></>}<th>Status</th></tr></thead>
        <tbody>
          {runs.map((run) => {
            const evaluation = run.evaluations.at(-1);
            return (
              <tr key={run.id}>
                <td><Link to={`/runs/${run.id}`}>#{run.id} · {run.source_type}</Link><small>{new Date(run.created_at).toLocaleDateString()}</small></td>
                <td><span className="tag">{run.prompt_version}</span></td>
                <td>{run.model_name}</td>
                <td><strong>{evaluation?.overall_score?.toFixed(1) ?? "—"}</strong></td>
                {!compact && <><td>${run.estimated_cost.toFixed(4)}</td><td>{run.latency_ms} ms</td></>}
                <td><span className={`status ${run.status}`}>{run.status}</span></td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {!runs.length && <p className="empty">No runs logged yet.</p>}
    </div>
  );
}
