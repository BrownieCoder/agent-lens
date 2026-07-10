from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.regression_case import RegressionCase
from ..models.run import WorkflowRun
from ..schemas.regression_case import RegressionCaseCreate, RegressionCaseRead
from ..schemas.run import RunRead

router = APIRouter(prefix="/regression-cases", tags=["regression"])


@router.post("", response_model=RegressionCaseRead, status_code=201)
def create_case(payload: RegressionCaseCreate, db: Session = Depends(get_db)) -> RegressionCase:
    case = RegressionCase(**payload.model_dump())
    db.add(case)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Regression case name already exists") from exc
    db.refresh(case)
    return case


@router.get("", response_model=list[RegressionCaseRead])
def list_cases(db: Session = Depends(get_db)) -> list[RegressionCase]:
    return list(db.scalars(select(RegressionCase).order_by(RegressionCase.created_at.desc())).all())


@router.get("/{case_id}", response_model=RegressionCaseRead)
def get_case(case_id: int, db: Session = Depends(get_db)) -> RegressionCase:
    case = db.get(RegressionCase, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Regression case not found")
    return case


@router.get("/{case_id}/runs", response_model=list[RunRead])
def get_case_runs(case_id: int, db: Session = Depends(get_db)) -> list[WorkflowRun]:
    if not db.get(RegressionCase, case_id):
        raise HTTPException(status_code=404, detail="Regression case not found")
    return list(
        db.scalars(
            select(WorkflowRun)
            .where(WorkflowRun.regression_case_id == case_id)
            .order_by(WorkflowRun.created_at.desc())
        ).all()
    )
