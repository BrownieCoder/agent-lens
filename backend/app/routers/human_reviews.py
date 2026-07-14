from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from ..db import get_db
from ..models.evaluation import Evaluation
from ..models.human_review import HumanReview
from ..models.run import WorkflowRun
from ..schemas.human_review import (
    CalibrationSummary,
    CalibrationScope,
    HumanReviewCreate,
    HumanReviewQueueItem,
    HumanReviewRead,
    HumanReviewUpdate,
)
from ..services.calibration import calibration_data

router = APIRouter(tags=["human reviews"])


@router.post("/runs/{run_id}/human-reviews", response_model=HumanReviewRead, status_code=201)
def create_human_review(
    run_id: int, payload: HumanReviewCreate, db: Session = Depends(get_db)
) -> HumanReview:
    if not db.get(WorkflowRun, run_id):
        raise HTTPException(status_code=404, detail="Run not found")
    evaluation = db.get(Evaluation, payload.evaluation_id)
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    if evaluation.run_id != run_id:
        raise HTTPException(status_code=422, detail="Evaluation does not belong to this run")
    duplicate = db.scalar(
        select(HumanReview).where(
            HumanReview.evaluation_id == payload.evaluation_id,
            HumanReview.reviewer == payload.reviewer,
        )
    )
    if duplicate:
        raise HTTPException(status_code=409, detail="Reviewer already reviewed this evaluation")
    review = HumanReview(**payload.model_dump())
    db.add(review)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Reviewer already reviewed this evaluation") from exc
    db.refresh(review)
    return review


@router.get("/runs/{run_id}/human-reviews", response_model=list[HumanReviewRead])
def list_human_reviews(
    run_id: int,
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[HumanReview]:
    if not db.get(WorkflowRun, run_id):
        raise HTTPException(status_code=404, detail="Run not found")
    return list(
        db.scalars(
            select(HumanReview)
            .join(Evaluation, Evaluation.id == HumanReview.evaluation_id)
            .where(Evaluation.run_id == run_id)
            .options(selectinload(HumanReview.evaluation))
            .order_by(HumanReview.created_at.desc())
            .offset(offset)
            .limit(limit)
        ).all()
    )


@router.get("/human-reviews/{review_id}", response_model=HumanReviewRead)
def get_human_review(review_id: int, db: Session = Depends(get_db)) -> HumanReview:
    review = db.get(HumanReview, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Human review not found")
    return review


@router.put("/human-reviews/{review_id}", response_model=HumanReviewRead)
def update_human_review(
    review_id: int, payload: HumanReviewUpdate, db: Session = Depends(get_db)
) -> HumanReview:
    review = db.get(HumanReview, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Human review not found")
    score_fields = {
        "clarity_score", "evidence_score", "risk_coverage_score", "specificity_score",
        "actionability_score", "novelty_score", "overall_score",
    }
    scores_changed = any(
        float(getattr(review, key)) != float(value)
        for key, value in payload.model_dump().items()
        if key in score_fields
    )
    values = payload.model_dump()
    if scores_changed:
        values["review_decision"] = "pending"
        review.scores_edited_after_reveal = True
    for key, value in values.items():
        setattr(review, key, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Reviewer already reviewed this evaluation") from exc
    db.refresh(review)
    return review


@router.get("/human-review-queue", response_model=list[HumanReviewQueueItem])
def human_review_queue(
    unreviewed: bool = True,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[dict]:
    latest_ids = select(func.max(Evaluation.id).label("id")).group_by(Evaluation.run_id).subquery()
    review_counts = (
        select(HumanReview.evaluation_id, func.count(HumanReview.id).label("review_count"))
        .group_by(HumanReview.evaluation_id)
        .subquery()
    )
    query = (
        select(WorkflowRun, Evaluation, func.coalesce(review_counts.c.review_count, 0))
        .join(latest_ids, latest_ids.c.id == Evaluation.id)
        .join(WorkflowRun, WorkflowRun.id == Evaluation.run_id)
        .outerjoin(review_counts, review_counts.c.evaluation_id == Evaluation.id)
    )
    if unreviewed:
        query = query.where(func.coalesce(review_counts.c.review_count, 0) == 0)
    query = query.order_by(WorkflowRun.created_at.desc(), Evaluation.id.desc())
    rows = db.execute(query.offset(offset).limit(limit)).all()
    return [
        {
            "run_id": run.id,
            "evaluation_id": evaluation.id,
            "workflow_name": run.workflow_name,
            "prompt_version": run.prompt_version,
            "model_name": run.model_name,
            "review_count": int(review_count),
            "created_at": run.created_at,
        }
        for run, evaluation, review_count in rows
    ]


@router.get("/dashboard/calibration", response_model=CalibrationSummary)
def calibration_summary(
    evaluator_model: str | None = None,
    rubric_version: str | None = None,
    workflow_name: str | None = None,
    prompt_version: str | None = None,
    db: Session = Depends(get_db),
) -> dict:
    scopes = calibration_scopes(db)
    if (evaluator_model is None) != (rubric_version is None):
        raise HTTPException(status_code=422, detail="evaluator_model and rubric_version must be provided together")
    if evaluator_model is None and len(scopes) > 1:
        raise HTTPException(status_code=400, detail="Select an evaluator model and rubric version")
    if evaluator_model is None and scopes:
        evaluator_model = scopes[0][0]
        rubric_version = scopes[0][1]
    return calibration_data(db, evaluator_model, rubric_version, workflow_name, prompt_version)


def calibration_scopes(db: Session) -> list[tuple[str, str, int]]:
    return [
        (model, rubric, int(count))
        for model, rubric, count in db.execute(
            select(Evaluation.evaluator_model, HumanReview.rubric_version, func.count(HumanReview.id))
            .join(HumanReview, HumanReview.evaluation_id == Evaluation.id)
            .group_by(Evaluation.evaluator_model, HumanReview.rubric_version)
            .order_by(Evaluation.evaluator_model, HumanReview.rubric_version)
        ).all()
    ]


@router.get("/dashboard/calibration/scopes", response_model=list[CalibrationScope])
def list_calibration_scopes(db: Session = Depends(get_db)) -> list[dict]:
    return [
        {"evaluator_model": model, "rubric_version": rubric, "review_count": count}
        for model, rubric, count in calibration_scopes(db)
    ]
