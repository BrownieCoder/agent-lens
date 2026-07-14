from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base

if TYPE_CHECKING:
    from .evaluation import Evaluation


class HumanReview(Base):
    __tablename__ = "human_reviews"
    __table_args__ = (
        UniqueConstraint("evaluation_id", "reviewer", name="uq_human_review_evaluation_reviewer"),
        CheckConstraint("review_decision IN ('pending', 'agree', 'adjust', 'reject')", name="ck_human_review_decision"),
        *(CheckConstraint(f"{name} >= 1 AND {name} <= 5", name=f"ck_human_review_{name}") for name in (
            "clarity_score", "evidence_score", "risk_coverage_score", "specificity_score",
            "actionability_score", "novelty_score", "overall_score",
        )),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    evaluation_id: Mapped[int] = mapped_column(
        ForeignKey("evaluations.id", ondelete="CASCADE"), index=True
    )
    reviewer: Mapped[str] = mapped_column(String(120), default="local-reviewer")
    review_decision: Mapped[str] = mapped_column(String(20), default="pending")
    rubric_version: Mapped[str] = mapped_column(String(80), default="research-report-v1")
    clarity_score: Mapped[float] = mapped_column(Float)
    evidence_score: Mapped[float] = mapped_column(Float)
    risk_coverage_score: Mapped[float] = mapped_column(Float)
    specificity_score: Mapped[float] = mapped_column(Float)
    actionability_score: Mapped[float] = mapped_column(Float)
    novelty_score: Mapped[float] = mapped_column(Float)
    overall_score: Mapped[float] = mapped_column(Float)
    notes: Mapped[str] = mapped_column(Text, default="")
    scores_edited_after_reveal: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    evaluation: Mapped["Evaluation"] = relationship(back_populates="human_reviews")

    @property
    def run_id(self) -> int:
        return self.evaluation.run_id
