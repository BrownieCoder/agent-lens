from __future__ import annotations

import math
from collections import Counter, defaultdict
from statistics import fmean

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models.evaluation import Evaluation
from ..models.human_review import HumanReview
from ..models.run import WorkflowRun


SCORE_DIMENSIONS = (
    "clarity_score",
    "evidence_score",
    "risk_coverage_score",
    "specificity_score",
    "actionability_score",
    "novelty_score",
    "overall_score",
)


def _round(value: float | None, digits: int = 3) -> float | None:
    return round(value, digits) if value is not None else None


def _correlation(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 2:
        return None
    mean_x, mean_y = fmean(xs), fmean(ys)
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True))
    denominator = math.sqrt(
        sum((x - mean_x) ** 2 for x in xs) * sum((y - mean_y) ** 2 for y in ys)
    )
    return numerator / denominator if denominator else None


def _dimension_metrics(pairs: list[tuple[float, float]], dimension: str) -> dict:
    if not pairs:
        return {
            "dimension": dimension,
            "sample_count": 0,
            "mae": None,
            "rmse": None,
            "bias": None,
            "judge_mean": None,
            "human_mean": None,
            "agreement_rate": None,
            "large_disagreement_rate": None,
            "overrating_rate": None,
            "underrating_rate": None,
            "correlation": None,
        }
    judges = [pair[0] for pair in pairs]
    humans = [pair[1] for pair in pairs]
    errors = [judge - human for judge, human in pairs]
    count = len(errors)
    return {
        "dimension": dimension,
        "sample_count": count,
        "mae": _round(fmean(abs(error) for error in errors)),
        "rmse": _round(math.sqrt(fmean(error**2 for error in errors))),
        "bias": _round(fmean(errors)),
        "judge_mean": _round(fmean(judges)),
        "human_mean": _round(fmean(humans)),
        "agreement_rate": _round(sum(abs(error) <= 0.5 for error in errors) / count),
        "large_disagreement_rate": _round(sum(abs(error) >= 1.0 for error in errors) / count),
        "overrating_rate": _round(sum(error >= 1.0 for error in errors) / count),
        "underrating_rate": _round(sum(error <= -1.0 for error in errors) / count),
        "correlation": _round(_correlation(judges, humans)),
    }


def calibration_data(
    db: Session,
    evaluator_model: str | None = None,
    rubric_version: str | None = None,
    workflow_name: str | None = None,
    prompt_version: str | None = None,
) -> dict:
    evaluation_filters = []
    if evaluator_model:
        evaluation_filters.append(Evaluation.evaluator_model == evaluator_model)
    if workflow_name:
        evaluation_filters.append(WorkflowRun.workflow_name == workflow_name)
    if prompt_version:
        evaluation_filters.append(WorkflowRun.prompt_version == prompt_version)
    review_filters = [*evaluation_filters]
    if rubric_version:
        review_filters.append(HumanReview.rubric_version == rubric_version)

    rows = db.execute(
        select(Evaluation, HumanReview, WorkflowRun)
        .join(HumanReview, HumanReview.evaluation_id == Evaluation.id)
        .join(WorkflowRun, WorkflowRun.id == Evaluation.run_id)
        .where(*review_filters)
        .order_by(Evaluation.id, HumanReview.id)
    ).all()

    evaluated_evaluation_count = int(
        db.scalar(
            select(func.count(Evaluation.id))
            .join(WorkflowRun, WorkflowRun.id == Evaluation.run_id)
            .where(*evaluation_filters)
        )
        or 0
    )
    evaluated_run_count = int(
        db.scalar(
            select(func.count(func.distinct(Evaluation.run_id)))
            .join(WorkflowRun, WorkflowRun.id == Evaluation.run_id)
            .where(*evaluation_filters)
        )
        or 0
    )

    grouped: dict[int, list[tuple[Evaluation, HumanReview, WorkflowRun]]] = defaultdict(list)
    for evaluation, review, run in rows:
        grouped[evaluation.id].append((evaluation, review, run))

    dimension_pairs: dict[str, list[tuple[float, float]]] = {
        dimension: [] for dimension in SCORE_DIMENSIONS
    }
    disagreements = []
    for items in grouped.values():
        evaluation, _, run = items[0]
        reviews = [item[1] for item in items]
        consensus = {
            dimension: fmean(float(getattr(review, dimension)) for review in reviews)
            for dimension in SCORE_DIMENSIONS
        }
        for dimension in SCORE_DIMENSIONS:
            dimension_pairs[dimension].append(
                (float(getattr(evaluation, dimension)), consensus[dimension])
            )
        signed_delta = float(evaluation.overall_score) - consensus["overall_score"]
        decisions = {review.review_decision for review in reviews}
        disagreements.append(
            {
                "run_id": run.id,
                "evaluation_id": evaluation.id,
                "prompt_version": run.prompt_version,
                "evaluator_model": evaluation.evaluator_model,
                "judge_overall": round(float(evaluation.overall_score), 3),
                "human_overall": round(consensus["overall_score"], 3),
                "signed_delta": round(signed_delta, 3),
                "absolute_delta": round(abs(signed_delta), 3),
                "decision": next(iter(decisions)) if len(decisions) == 1 else "mixed",
                "review_date": max(review.updated_at for review in reviews),
                "dangerous": evaluation.overall_score >= 4.0 and consensus["overall_score"] <= 2.5,
            }
        )

    disagreements.sort(key=lambda item: item["absolute_delta"], reverse=True)
    dimensions = [
        _dimension_metrics(dimension_pairs[dimension], dimension) for dimension in SCORE_DIMENSIONS
    ]
    overall = next(item for item in dimensions if item["dimension"] == "overall_score")
    decision_counts = Counter(review.review_decision for _, review, _ in rows)
    decided_count = sum(decision_counts[name] for name in ("agree", "adjust", "reject"))
    acceptance_rate = decision_counts["agree"] / decided_count if decided_count else None

    reviewed_run_count = len({run.id for _, _, run in rows})
    dangerous_samples = [item for item in disagreements if item["dangerous"]]
    return {
        "evaluator_model": evaluator_model,
        "rubric_version": rubric_version,
        "review_count": len(rows),
        "calibrated_evaluation_count": len(grouped),
        "reviewer_count": len({review.reviewer for _, review, _ in rows}),
        "evaluated_evaluation_count": evaluated_evaluation_count,
        "reviewed_evaluation_count": len(grouped),
        "evaluation_coverage_rate": round(len(grouped) / evaluated_evaluation_count, 3)
        if evaluated_evaluation_count
        else None,
        "evaluated_run_count": evaluated_run_count,
        "reviewed_run_count": reviewed_run_count,
        "run_coverage_rate": round(reviewed_run_count / evaluated_run_count, 3)
        if evaluated_run_count
        else None,
        "overall_mae": overall["mae"],
        "overall_rmse": overall["rmse"],
        "overall_bias": overall["bias"],
        "acceptance_rate": _round(acceptance_rate),
        "overall_agreement_rate": overall["agreement_rate"],
        "overall_large_disagreement_rate": overall["large_disagreement_rate"],
        "overall_correlation": overall["correlation"],
        "decision_counts": {
            name: decision_counts[name] for name in ("pending", "agree", "adjust", "reject")
        },
        "dimensions": dimensions,
        "disagreements": disagreements[:20],
        "dangerous_samples": dangerous_samples,
    }
