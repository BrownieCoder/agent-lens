from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base, UTCDateTime

if TYPE_CHECKING:
    from .evaluation import Evaluation


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    workflow_name: Mapped[str] = mapped_column(String(120), index=True)
    source_type: Mapped[str] = mapped_column(String(80), index=True)
    input_text: Mapped[str] = mapped_column(Text)
    output_text: Mapped[str] = mapped_column(Text)
    prompt_version: Mapped[str] = mapped_column(String(120), index=True)
    model_name: Mapped[str] = mapped_column(String(120), index=True)
    provider: Mapped[str] = mapped_column(String(80), default="openai")
    token_input: Mapped[int | None] = mapped_column(Integer, nullable=True)
    token_output: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="success", index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    regression_case_id: Mapped[int | None] = mapped_column(ForeignKey("regression_cases.id"), nullable=True, index=True)
    usage_source: Mapped[str] = mapped_column(String(40), default="caller-reported")
    legacy_usage: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    prompt_template_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    generation_parameters: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    dataset_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    experiment_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    last_evaluation_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, index=True)

    evaluation_attempts = relationship("EvaluationAttempt", cascade="all, delete-orphan")

    evaluations: Mapped[list["Evaluation"]] = relationship(
        back_populates="run", cascade="all, delete-orphan", order_by="Evaluation.created_at"
    )
