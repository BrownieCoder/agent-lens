from datetime import date


def render_markdown_summary(summary: dict, prompt_rows: list[dict], date_from: date | None, date_to: date | None) -> str:
    period = f"{date_from or 'beginning'} to {date_to or 'present'}"
    ranked = sorted(prompt_rows, key=lambda row: row.get("average_overall_score") or 0, reverse=True)
    best = ranked[0]["prompt_version"] if ranked else "N/A"
    worst = ranked[-1]["prompt_version"] if ranked else "N/A"
    flags = summary.get("common_flags", {})
    common = sorted(flags.items(), key=lambda item: item[1], reverse=True)
    patterns = ", ".join(f"{name}: {count}" for name, count in common if count) or "No evaluated failure flags"

    recommendations: list[str] = []
    if summary.get("failure_rate", 0) > 0.05:
        recommendations.append("Investigate failed runs and add representative cases to the regression set.")
    if flags.get("weak_evidence", 0):
        recommendations.append("Require citations or source-linked evidence in the generation prompt.")
    if flags.get("missing_risks", 0):
        recommendations.append("Add an explicit downside and uncertainty section to the report contract.")
    if not recommendations:
        recommendations.append("Expand the regression set and monitor for prompt-version regressions.")

    rows = "\n".join(
        f"| {row['prompt_version']} | {row['run_count']} | {row['average_overall_score'] or 'N/A'} | "
        f"${row['average_cost']:.4f} | {row['average_latency_ms']:.0f} ms | {row['failure_rate']:.1%} |"
        for row in prompt_rows
    ) or "| No data | 0 | N/A | $0 | 0 ms | 0% |"
    recs = "\n".join(f"- {item}" for item in recommendations)
    return f"""# Agent Lens Evaluation Summary

**Date range:** {period}
**Runs:** {summary.get('total_runs', 0)}
**Average overall score:** {summary.get('average_overall_score') or 'N/A'}
**Average cost:** ${summary.get('average_cost', 0):.4f}
**Average latency:** {summary.get('average_latency_ms', 0):.0f} ms
**Failure rate:** {summary.get('failure_rate', 0):.1%}

## Prompt Versions

| Prompt | Runs | Score | Cost | Latency | Failure rate |
|---|---:|---:|---:|---:|---:|
{rows}

- Best-performing prompt: **{best}**
- Worst-performing prompt: **{worst}**

## Common Failure Patterns

{patterns}

## Recommended Next Actions

{recs}
"""
