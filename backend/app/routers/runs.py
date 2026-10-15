from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, or_, cast, String
from sqlalchemy.orm import Session, selectinload

from ..db import get_db
from ..models.run import WorkflowRun
from ..models.evaluation import Evaluation
from ..models.human_review import HumanReview
from ..models.regression_case import RegressionCase
from ..schemas.human_review import HumanReviewRead
from ..services.analytics import _date_filters
from ..schemas.run import RunCreate, RunRead

router = APIRouter(prefix="/runs", tags=["runs"])


@router.post("", response_model=RunRead, status_code=201)
def create_run(payload: RunCreate, db: Session = Depends(get_db)) -> WorkflowRun:
    if payload.regression_case_id is not None and not db.get(RegressionCase, payload.regression_case_id):
        raise HTTPException(status_code=422, detail="Regression case not found")
    run = WorkflowRun(**payload.model_dump())
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


@router.get("", response_model=list[RunRead])
def list_runs(
    q: str | None = Query(default=None, max_length=200),
    date_from: date | None = None,
    date_to: date | None = None,
    workflow_name: str | None = None,
    prompt_version: str | None = None,
    model_name: str | None = None,
    status: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[WorkflowRun]:
    query = select(WorkflowRun).options(selectinload(WorkflowRun.evaluations))
    for column, value in (
        (WorkflowRun.workflow_name, workflow_name),
        (WorkflowRun.prompt_version, prompt_version),
        (WorkflowRun.model_name, model_name),
        (WorkflowRun.status, status),
    ):
        if value:
            query = query.where(column == value)
    if q:
        query = query.where(or_(*(column.contains(q, autoescape=True) for column in (cast(WorkflowRun.id, String), WorkflowRun.workflow_name, WorkflowRun.source_type, WorkflowRun.prompt_version, WorkflowRun.model_name))))
    query = query.where(*_date_filters(date_from, date_to)).order_by(WorkflowRun.id.desc()).offset(offset).limit(limit)
    return list(db.scalars(query).all())


@router.get("/{run_id}", response_model=RunRead)
def get_run(run_id: int, db: Session = Depends(get_db)) -> WorkflowRun:
    run = db.scalar(
        select(WorkflowRun)
        .where(WorkflowRun.id == run_id)
        .options(selectinload(WorkflowRun.evaluations))
    )
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.get("/{run_id}/blind")
def get_blind_run(run_id: int, evaluation_id: int | None = Query(default=None, gt=0), db: Session = Depends(get_db)) -> dict:
    run = db.get(WorkflowRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if evaluation_id is not None:
        evaluation = db.get(Evaluation, evaluation_id)
        if not evaluation or evaluation.run_id != run_id:
            raise HTTPException(status_code=404, detail="Evaluation not found for this run")
    else:
        evaluation = db.scalar(select(Evaluation).where(Evaluation.run_id == run_id).order_by(Evaluation.id.desc()).limit(1))
    # Construct from columns explicitly: never serialize ORM relationships here.
    run_data = {column.name: getattr(run, column.name) for column in WorkflowRun.__table__.columns}
    run_data["evaluations"] = []
    review = db.scalar(select(HumanReview).where(HumanReview.evaluation_id == evaluation.id, HumanReview.reviewer == "local-reviewer")) if evaluation else None
    return {
        "run": run_data,
        "evaluation": {key: getattr(evaluation, key) for key in ("id", "run_id", "evaluator_type", "evaluator_model", "rubric_version", "created_at")} if evaluation else None,
        "review": HumanReviewRead.model_validate(review).model_dump() if review else None,
    }
