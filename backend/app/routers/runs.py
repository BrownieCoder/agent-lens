from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..db import get_db
from ..models.run import WorkflowRun
from ..schemas.run import RunCreate, RunRead

router = APIRouter(prefix="/runs", tags=["runs"])


@router.post("", response_model=RunRead, status_code=201)
def create_run(payload: RunCreate, db: Session = Depends(get_db)) -> WorkflowRun:
    run = WorkflowRun(**payload.model_dump())
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


@router.get("", response_model=list[RunRead])
def list_runs(
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
    query = query.order_by(WorkflowRun.created_at.desc()).offset(offset).limit(limit)
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
