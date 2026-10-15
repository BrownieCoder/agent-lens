from datetime import date

from .analytics import COMPARISON_NOTE


def _value(value, kind="number"):
    if value is None:
        return "N/A"
    if kind == "cost":
        return f"${value:.4f}"
    if kind == "latency":
        return f"{value:.0f} ms"
    if kind == "rate":
        return f"{value:.1%}"
    return str(value)


def _text(value):
    return str(value).replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ").replace("\r", " ").replace("<", "&lt;").replace(">", "&gt;")


def render_markdown_summary(summary: dict, prompt_rows: list[dict], date_from: date | None, date_to: date | None) -> str:
    period = f"{date_from or 'beginning'} to {date_to or 'present'} (UTC)"
    rows = "\n".join(
        f"| {_text(row['prompt_version'])} | {row['run_count']} | {row['evaluated_count']} | {_value(row['average_overall_score'])} | "
        f"{_value(row['average_cost'], 'cost')} (n={row['cost_sample_count']}) | {_value(row['average_latency_ms'], 'latency')} (n={row['latency_sample_count']}) | "
        f"{_value(row['failure_rate'], 'rate')} | {row['matched_input_count']} / {row['unpaired_input_count']} / {row['duplicate_input_count']} |"
        for row in prompt_rows
    ) or "| No data | 0 | 0 | N/A | N/A | N/A | N/A | 0 / 0 / 0 |"
    confounds = "\n".join(
        f"- {_text(row['prompt_version'])}: workflows={_text(', '.join(row['workflows']))}; generation models={_text(', '.join(row['models']))}; "
        f"judges={_text(', '.join(row['evaluator_models']))}; judge rubrics={_text(', '.join(row['judge_rubric_versions']))}; reevaluations={row['reevaluation_count']}; missing reproducibility metadata={row['missing_provenance_count']}; datasets={_text(', '.join(row['datasets'])) or 'not recorded'}; experiments={_text(', '.join(row['experiments'])) or 'not recorded'}."
        for row in prompt_rows
    )
    patterns = ", ".join(f"{name}: {count}" for name, count in summary.get("common_flags", {}).items() if count) or "No evaluated failure flags"
    return f"""# Agent Lens Evaluation Summary

**Date range:** {period}
**Runs:** {summary.get('total_runs', 0)}
**Evaluated runs:** {summary.get('evaluated_count', 0)}
**Failed / pending judge attempts:** {summary.get('failed_evaluation_attempt_count', 0)} / {summary.get('pending_evaluation_attempt_count', 0)}
**Average overall score:** {_value(summary.get('average_overall_score'))}
**Average generation cost (USD):** {_value(summary.get('average_cost'), 'cost')} (n={summary.get('cost_sample_count', 0)})
**Average generation latency:** {_value(summary.get('average_latency_ms'), 'latency')} (n={summary.get('latency_sample_count', 0)})
**Failure rate:** {_value(summary.get('failure_rate'), 'rate')}

Costs, tokens and latency are caller-reported generation measurements; unknown values are excluded from means. Judge/retry cost is not measured. Mock measurements are synthetic, not billing evidence. Legacy usage records: {summary.get("legacy_usage_count", 0)}; ambiguous legacy zeros are excluded as unknown, with original measurements preserved separately.

## Prompt Versions

{COMPARISON_NOTE}

| Prompt | Runs | Evaluated | Score | Cost | Latency | Failure rate | Matched / unpaired / duplicates |
|---|---:|---:|---:|---:|---:|---:|---:|
{rows}

{confounds}

## Common Failure Patterns

{patterns}

## Recommended Next Actions

Review flagged outputs and compare controlled, matched inputs before changing prompts. Evaluator scores and human labels are review evidence, not verified external facts or ground truth.
"""
