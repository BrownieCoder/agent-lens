from datetime import date, datetime, time, timezone

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from ..models.evaluation import Evaluation
from ..models.run import WorkflowRun


FLAG_NAMES = (
    "possible_hallucination",
    "too_generic",
    "missing_risks",
    "overconfident_language",
    "weak_evidence",
    "needs_human_review",
)


def _latest_evaluations():
    latest_ids = select(func.max(Evaluation.id).label("id")).group_by(Evaluation.run_id).subquery()
    return select(Evaluation).join(latest_ids, Evaluation.id == latest_ids.c.id).subquery()


def _date_filters(date_from: date | None = None, date_to: date | None = None):
    filters = []
    if date_from:
        filters.append(WorkflowRun.created_at >= datetime.combine(date_from, time.min, tzinfo=timezone.utc))
    if date_to:
        filters.append(WorkflowRun.created_at <= datetime.combine(date_to, time.max, tzinfo=timezone.utc))
    return filters


def summary_data(db: Session, date_from: date | None = None, date_to: date | None = None) -> dict:
    ev = _latest_evaluations()
    filters = _date_filters(date_from, date_to)
    row = db.execute(
        select(
            func.count(WorkflowRun.id),
            func.avg(ev.c.overall_score),
            func.avg(WorkflowRun.estimated_cost),
            func.avg(WorkflowRun.latency_ms),
            func.avg(case((WorkflowRun.status != "success", 1.0), else_=0.0)),
        )
        .outerjoin(ev, ev.c.run_id == WorkflowRun.id)
        .where(*filters)
    ).one()
    flags = {
        name: int(
            db.scalar(
                select(func.count()).select_from(WorkflowRun).join(ev, ev.c.run_id == WorkflowRun.id).where(
                    *filters, getattr(ev.c, name).is_(True)
                )
            )
            or 0
        )
        for name in FLAG_NAMES
    }
    return {
        "total_runs": int(row[0] or 0),
        "average_overall_score": round(float(row[1]), 2) if row[1] is not None else None,
        "average_cost": round(float(row[2] or 0), 6),
        "average_latency_ms": round(float(row[3] or 0), 1),
        "failure_rate": round(float(row[4] or 0), 4),
        "common_flags": flags,
    }


def prompt_comparison_data(db: Session, date_from: date | None = None, date_to: date | None = None) -> list[dict]:
    ev = _latest_evaluations()
    filters = _date_filters(date_from, date_to)
    score_columns = (
        "clarity_score",
        "evidence_score",
        "risk_coverage_score",
        "specificity_score",
        "actionability_score",
        "novelty_score",
        "overall_score",
    )
    query = (
        select(
            WorkflowRun.prompt_version,
            func.count(WorkflowRun.id).label("run_count"),
            *(func.avg(getattr(ev.c, name)).label(name) for name in score_columns),
            func.avg(WorkflowRun.estimated_cost).label("average_cost"),
            func.avg(WorkflowRun.latency_ms).label("average_latency_ms"),
            func.avg(case((WorkflowRun.status != "success", 1.0), else_=0.0)).label("failure_rate"),
        )
        .outerjoin(ev, ev.c.run_id == WorkflowRun.id)
        .where(*filters)
        .group_by(WorkflowRun.prompt_version)
        .order_by(func.avg(ev.c.overall_score).desc())
    )
    results = []
    for row in db.execute(query).mappings():
        item = dict(row)
        for name in score_columns:
            item[f"average_{name}"] = round(float(item.pop(name)), 2) if item[name] is not None else None
        item["average_cost"] = round(float(item["average_cost"] or 0), 6)
        item["average_latency_ms"] = round(float(item["average_latency_ms"] or 0), 1)
        item["failure_rate"] = round(float(item["failure_rate"] or 0), 4)
        results.append(item)
    return results
