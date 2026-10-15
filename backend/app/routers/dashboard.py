from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.evaluation import Evaluation
from ..models.run import WorkflowRun
from ..schemas.run import RunRead
from ..services.analytics import prompt_comparison_data, summary_data, _date_filters

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
def get_summary(
    date_from: date | None = None, date_to: date | None = None, db: Session = Depends(get_db)
) -> dict:
    return summary_data(db, date_from, date_to)


@router.get("/trends")
def get_trends(days: int | None = Query(default=None, ge=1, le=365), date_from: date | None = None, date_to: date | None = None, db: Session = Depends(get_db)) -> list[dict]:
    latest_ids = select(func.max(Evaluation.id).label("id")).group_by(Evaluation.run_id).subquery()
    latest = select(Evaluation).join(latest_ids, Evaluation.id == latest_ids.c.id).subquery()
    if days is not None and date_from is None and date_to is None:
        date_to = datetime.now(timezone.utc).date()
        date_from = date_to - timedelta(days=days - 1)
    day = func.date(WorkflowRun.created_at).label("day")
    rows = db.execute(
        select(
            day,
            func.count(WorkflowRun.id).label("run_count"),
            func.count(WorkflowRun.estimated_cost).label("cost_sample_count"),
            func.count(WorkflowRun.latency_ms).label("latency_sample_count"),
            func.count(latest.c.id).label("evaluated_count"),
            func.avg(WorkflowRun.estimated_cost).label("average_cost"),
            func.avg(WorkflowRun.latency_ms).label("average_latency_ms"),
            func.avg(case((WorkflowRun.status != "success", 1.0), else_=0.0)).label("failure_rate"),
            func.avg(latest.c.overall_score).label("average_overall_score"),
        )
        .outerjoin(latest, latest.c.run_id == WorkflowRun.id)
        .where(*_date_filters(date_from, date_to))
        .group_by(day)
        .order_by(day.desc())
    ).mappings()
    return [dict(row) for row in reversed(list(rows))]


@router.get("/prompt-comparison")
def prompt_comparison(
    date_from: date | None = None, date_to: date | None = None, db: Session = Depends(get_db)
) -> list[dict]:
    return prompt_comparison_data(db, date_from, date_to)


@router.get("/ranked-runs", response_model=dict[str, list[RunRead]])
def ranked_runs(limit: int = Query(default=5, ge=1, le=20), date_from: date | None = None, date_to: date | None = None, db: Session = Depends(get_db)) -> dict:
    latest_ids = select(func.max(Evaluation.id).label("id")).group_by(Evaluation.run_id).subquery()
    latest = select(Evaluation).join(latest_ids, Evaluation.id == latest_ids.c.id).subquery()
    base = select(WorkflowRun).join(latest, latest.c.run_id == WorkflowRun.id).where(*_date_filters(date_from, date_to))
    best = list(db.scalars(base.order_by(latest.c.overall_score.desc()).limit(limit)).all())
    worst = list(db.scalars(base.order_by(latest.c.overall_score.asc()).limit(limit)).all())
    return {"best": best, "worst": worst}
