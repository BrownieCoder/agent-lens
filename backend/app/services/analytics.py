from collections import Counter, defaultdict
from datetime import date, datetime, time, timezone
from statistics import fmean

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..models.evaluation import Evaluation
from ..models.run import WorkflowRun

FLAG_NAMES = ("possible_hallucination", "too_generic", "missing_risks", "overconfident_language", "weak_evidence", "needs_human_review")
SCORE_NAMES = ("clarity_score", "evidence_score", "risk_coverage_score", "specificity_score", "actionability_score", "novelty_score", "overall_score")
COMPARISON_NOTE = ("Observational cohorts, not causal prompt improvement. Matched inputs are exact input-text matches "
                   "across at least two prompt versions; duplicates are additional runs of an input within a version. "
                   "Scores use the latest evaluation per run; failures remain in run denominators. Models, workflows and "
                   "judges may differ. Optional caller-provided dataset/experiment/parameter metadata is not a verified registry; missing provenance is counted explicitly.")


def _latest_evaluations():
    latest_ids = select(func.max(Evaluation.id).label("id")).group_by(Evaluation.run_id).subquery()
    return select(Evaluation).join(latest_ids, Evaluation.id == latest_ids.c.id).subquery()


def _date_filters(date_from: date | None = None, date_to: date | None = None):
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=422, detail="date_from must not be after date_to")
    filters = []
    if date_from:
        filters.append(WorkflowRun.created_at >= datetime.combine(date_from, time.min, tzinfo=timezone.utc))
    if date_to:
        filters.append(WorkflowRun.created_at <= datetime.combine(date_to, time.max, tzinfo=timezone.utc))
    return filters


def _mean(values, digits=2):
    known = [value for value in values if value is not None]
    return round(fmean(known), digits) if known else None


def _runs(db, date_from, date_to):
    return list(db.scalars(select(WorkflowRun).where(*_date_filters(date_from, date_to)).options(selectinload(WorkflowRun.evaluations), selectinload(WorkflowRun.evaluation_attempts))).all())


def _metrics(runs):
    evaluations = [max(run.evaluations, key=lambda ev: ev.id) for run in runs if run.evaluations]
    # Modern successful attempts already represent their linked evaluation.
    # Legacy successes lack those rows; add only evaluations not represented by
    # an attempt, so new failures/pending requests cannot hide historical work.
    attempt_count = 0
    for run in runs:
        represented = {attempt.evaluation_id for attempt in run.evaluation_attempts if attempt.evaluation_id is not None}
        attempt_count += len(run.evaluation_attempts) + sum(evaluation.id not in represented for evaluation in run.evaluations)
    return {
        "run_count": len(runs),
        "evaluated_count": len(evaluations),
        "evaluation_attempt_count": attempt_count,
        "failed_evaluation_attempt_count": sum(attempt.status == "failed" for run in runs for attempt in run.evaluation_attempts),
        "pending_evaluation_attempt_count": sum(attempt.status == "pending" for run in runs for attempt in run.evaluation_attempts),
        "reevaluation_count": sum(max(len(run.evaluations) - 1, 0) for run in runs),
        "legacy_usage_count": sum(run.usage_source == "legacy-unverified" for run in runs),
        "cost_sample_count": sum(run.estimated_cost is not None for run in runs),
        "latency_sample_count": sum(run.latency_ms is not None for run in runs),
        "average_cost": _mean([run.estimated_cost for run in runs], 6),
        "average_latency_ms": _mean([run.latency_ms for run in runs], 1),
        "failure_rate": round(sum(run.status != "success" for run in runs) / len(runs), 4) if runs else None,
        **{f"average_{name}": _mean([getattr(ev, name) for ev in evaluations]) for name in SCORE_NAMES},
    }


def summary_data(db: Session, date_from: date | None = None, date_to: date | None = None) -> dict:
    runs = _runs(db, date_from, date_to)
    result = _metrics(runs)
    result["total_runs"] = result.pop("run_count")
    latest = [max(run.evaluations, key=lambda ev: ev.id) for run in runs if run.evaluations]
    result["common_flags"] = {name: sum(bool(getattr(ev, name)) for ev in latest) for name in FLAG_NAMES}
    return result


def prompt_comparison_data(db: Session, date_from: date | None = None, date_to: date | None = None) -> list[dict]:
    runs = _runs(db, date_from, date_to)
    groups = defaultdict(list)
    versions_by_input = defaultdict(set)
    for run in runs:
        groups[run.prompt_version].append(run)
        versions_by_input[run.input_text].add(run.prompt_version)
    results = []
    for version, cohort in sorted(groups.items()):
        inputs = Counter(run.input_text for run in cohort)
        matched = sum(len(versions_by_input[text]) > 1 for text in inputs)
        latest = [max(run.evaluations, key=lambda ev: ev.id) for run in cohort if run.evaluations]
        results.append({
            "prompt_version": version, **_metrics(cohort),
            "unique_input_count": len(inputs), "matched_input_count": matched,
            "unpaired_input_count": len(inputs) - matched,
            "duplicate_input_count": sum(count - 1 for count in inputs.values()),
            "workflows": sorted({run.workflow_name for run in cohort}),
            "models": sorted({run.model_name for run in cohort}),
            "evaluator_models": sorted({ev.evaluator_model for ev in latest}),
            "judge_rubric_versions": sorted({ev.rubric_version for ev in latest}),
            "datasets": sorted({run.dataset_name for run in cohort if run.dataset_name}),
            "experiments": sorted({run.experiment_name for run in cohort if run.experiment_name}),
            "missing_provenance_count": sum(run.prompt_template_hash is None or run.generation_parameters is None for run in cohort),
            "note": COMPARISON_NOTE,
        })
    return results
