from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EvaluationRequest(BaseModel):
    evaluator_type: str | None = None


class EvaluationPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    clarity_score: float = Field(ge=1, le=5)
    evidence_score: float = Field(ge=1, le=5)
    risk_coverage_score: float = Field(ge=1, le=5)
    specificity_score: float = Field(ge=1, le=5)
    actionability_score: float = Field(ge=1, le=5)
    novelty_score: float = Field(ge=1, le=5)
    overall_score: float = Field(ge=1, le=5)
    possible_hallucination: bool
    too_generic: bool
    missing_risks: bool
    overconfident_language: bool
    weak_evidence: bool
    needs_human_review: bool
    comments: str


class EvaluationRead(EvaluationPayload):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: int
    evaluator_type: str
    evaluator_model: str
    created_at: datetime
