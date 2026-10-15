from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EvaluationRequest(BaseModel):
    evaluator_type: str | None = Field(default=None, max_length=40)
    request_id: str | None = Field(default=None, min_length=1, max_length=120)


class EvaluationPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)

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
    comments: str = Field(min_length=1, max_length=8000)


    @field_validator("comments")
    @classmethod
    def nonblank_comments(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("comments must not be blank")
        return value


class EvaluationRead(EvaluationPayload):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: int
    evaluator_type: str
    evaluator_model: str
    rubric_version: str = "research-report-v1"
    created_at: datetime
