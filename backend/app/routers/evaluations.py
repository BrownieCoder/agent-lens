from threading import Lock
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..models.evaluation import Evaluation
from ..models.evaluation_attempt import EvaluationAttempt
from ..models.run import WorkflowRun
from ..schemas.evaluation import EvaluationRead, EvaluationRequest
from ..services.evaluator import ProviderEvaluationError, get_evaluator

router = APIRouter(prefix="/runs", tags=["evaluations"])
# Supported deployment is one process/worker. A nonblocking gate bounds paid work
# and prevents overlapping duplicate invocations, even without an idempotency key.
_evaluation_gate = Lock()


@router.post("/{run_id}/evaluate", response_model=EvaluationRead, status_code=201)
def evaluate_run(run_id: int, request: EvaluationRequest | None = None, db: Session = Depends(get_db)) -> Evaluation:
    if not _evaluation_gate.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="An evaluation is in progress; wait before retrying")
    try:
        run = db.get(WorkflowRun, run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        if run.status != "success" or not run.output_text.strip():
            raise HTTPException(status_code=422, detail="Only successful runs with output can be evaluated")
        settings = get_settings()
        backend = request.evaluator_type if request and request.evaluator_type else settings.evaluator_backend
        if backend in {"openai", "deepseek"} and not (request and request.request_id):
            raise HTTPException(status_code=422, detail="Hosted evaluators require a stable request_id; reuse it when retrying the same request")
        request_id = request.request_id if request and request.request_id else str(uuid4())
        attempt = db.scalar(select(EvaluationAttempt).where(EvaluationAttempt.request_id == request_id))
        if attempt:
            if attempt.run_id != run_id or attempt.backend != backend:
                raise HTTPException(status_code=409, detail="Request ID is already bound to a different evaluation request")
            if attempt.status == "success":
                return db.get(Evaluation, attempt.evaluation_id)
            raise HTTPException(status_code=409, detail="This request was already attempted; inspect its result before explicitly starting a new request")
        try:
            evaluator = get_evaluator(backend, settings)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        attempt = EvaluationAttempt(request_id=request_id, run_id=run_id, backend=backend, status="pending")
        db.add(attempt)
        db.commit()  # Reserve before any external call; crash recovery must not repeat it.
        try:
            result = evaluator.evaluate(run)
        except (ProviderEvaluationError, ValueError) as exc:
            attempt.status = "failed"
            run.last_evaluation_error = "Evaluation failed; no score was saved. Provider response details are not retained."
            db.commit()
            raise HTTPException(status_code=502, detail=str(exc) if isinstance(exc, ProviderEvaluationError) else "Evaluator returned an invalid result") from exc
        evaluation = Evaluation(run_id=run.id, evaluator_type=result.evaluator_type,
                                evaluator_model=result.evaluator_model, request_id=request_id,
                                **result.payload.model_dump())
        db.add(evaluation)
        db.flush()
        attempt.status = "success"
        attempt.evaluation_id = evaluation.id
        run.last_evaluation_error = None
        db.commit()
        db.refresh(evaluation)
        return evaluation
    finally:
        _evaluation_gate.release()


@router.get("/{run_id}/evaluation", response_model=EvaluationRead)
def get_latest_evaluation(run_id: int, db: Session = Depends(get_db)) -> Evaluation:
    if not db.get(WorkflowRun, run_id):
        raise HTTPException(status_code=404, detail="Run not found")
    evaluation = db.scalar(select(Evaluation).where(Evaluation.run_id == run_id).order_by(Evaluation.id.desc()).limit(1))
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    return evaluation


@router.get("/{run_id}/evaluation-attempts")
def list_evaluation_attempts(run_id: int, db: Session = Depends(get_db)) -> list[dict]:
    if not db.get(WorkflowRun, run_id):
        raise HTTPException(status_code=404, detail="Run not found")
    attempts = db.scalars(select(EvaluationAttempt).where(EvaluationAttempt.run_id == run_id).order_by(EvaluationAttempt.id.desc()).limit(100)).all()
    return [{key: getattr(attempt, key) for key in ("id", "request_id", "backend", "status", "evaluation_id", "created_at")} for attempt in attempts]
