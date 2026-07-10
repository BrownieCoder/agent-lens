from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..models.evaluation import Evaluation
from ..models.run import WorkflowRun
from ..schemas.evaluation import EvaluationRead, EvaluationRequest
from ..services.evaluator import ProviderEvaluationError, get_evaluator

router = APIRouter(prefix="/runs", tags=["evaluations"])


@router.post("/{run_id}/evaluate", response_model=EvaluationRead, status_code=201)
def evaluate_run(run_id: int, request: EvaluationRequest | None = None, db: Session = Depends(get_db)) -> Evaluation:
    run = db.get(WorkflowRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    settings = get_settings()
    backend = request.evaluator_type if request and request.evaluator_type else settings.evaluator_backend
    try:
        result = get_evaluator(backend, settings).evaluate(run)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ProviderEvaluationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    evaluation = Evaluation(
        run_id=run.id,
        evaluator_type=result.evaluator_type,
        evaluator_model=result.evaluator_model,
        **result.payload.model_dump(),
    )
    db.add(evaluation)
    db.commit()
    db.refresh(evaluation)
    return evaluation


@router.get("/{run_id}/evaluation", response_model=EvaluationRead)
def get_latest_evaluation(run_id: int, db: Session = Depends(get_db)) -> Evaluation:
    if not db.get(WorkflowRun, run_id):
        raise HTTPException(status_code=404, detail="Run not found")
    evaluation = db.scalar(
        select(Evaluation).where(Evaluation.run_id == run_id).order_by(Evaluation.created_at.desc()).limit(1)
    )
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    return evaluation
