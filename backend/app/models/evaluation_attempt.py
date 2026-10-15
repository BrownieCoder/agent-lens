from datetime import datetime, timezone

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from ..db import Base, UTCDateTime


class EvaluationAttempt(Base):
    """Durable reservation: an uncertain provider attempt is never retried implicitly."""
    __tablename__ = "evaluation_attempts"
    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[str] = mapped_column(String(160), unique=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("workflow_runs.id"))
    backend: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    evaluation_id: Mapped[int | None] = mapped_column(ForeignKey("evaluations.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=lambda: datetime.now(timezone.utc))
