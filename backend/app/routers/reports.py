from datetime import date

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..services.analytics import prompt_comparison_data, summary_data
from ..services.report_exporter import render_markdown_summary

router = APIRouter(prefix="/reports", tags=["reports"])


class ReportRequest(BaseModel):
    date_from: date | None = None
    date_to: date | None = None


@router.post("/evaluation-summary", response_class=PlainTextResponse)
def evaluation_summary(payload: ReportRequest, db: Session = Depends(get_db)) -> str:
    summary = summary_data(db, payload.date_from, payload.date_to)
    comparison = prompt_comparison_data(db, payload.date_from, payload.date_to)
    return render_markdown_summary(summary, comparison, payload.date_from, payload.date_to)
