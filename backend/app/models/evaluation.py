from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base

if TYPE_CHECKING:
    from .human_review import HumanReview
    from .run import WorkflowRun


class Evaluation(Base):
    __tablename__ = "evaluations"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("workflow_runs.id"), index=True)
    evaluator_type: Mapped[str] = mapped_column(String(40), default="mock")
    evaluator_model: Mapped[str] = mapped_column(String(120), default="mock-v1")
    clarity_score: Mapped[float] = mapped_column(Float)
    evidence_score: Mapped[float] = mapped_column(Float)
    risk_coverage_score: Mapped[float] = mapped_column(Float)
    specificity_score: Mapped[float] = mapped_column(Float)
    actionability_score: Mapped[float] = mapped_column(Float)
    novelty_score: Mapped[float] = mapped_column(Float)
    overall_score: Mapped[float] = mapped_column(Float, index=True)
    possible_hallucination: Mapped[bool] = mapped_column(Boolean, default=False)
    too_generic: Mapped[bool] = mapped_column(Boolean, default=False)
    missing_risks: Mapped[bool] = mapped_column(Boolean, default=False)
    overconfident_language: Mapped[bool] = mapped_column(Boolean, default=False)
    weak_evidence: Mapped[bool] = mapped_column(Boolean, default=False)
    needs_human_review: Mapped[bool] = mapped_column(Boolean, default=False)
    comments: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )

    run: Mapped["WorkflowRun"] = relationship(back_populates="evaluations")
    human_reviews: Mapped[list["HumanReview"]] = relationship(
        back_populates="evaluation", cascade="all, delete-orphan"
    )
