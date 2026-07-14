from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class HumanReviewPayload(BaseModel):
    reviewer: str = Field(default="local-reviewer", min_length=1, max_length=120)
    review_decision: Literal["pending", "agree", "adjust", "reject"] = "pending"
    rubric_version: str = Field(default="research-report-v1", min_length=1, max_length=80)
    clarity_score: float = Field(ge=1, le=5)
    evidence_score: float = Field(ge=1, le=5)
    risk_coverage_score: float = Field(ge=1, le=5)
    specificity_score: float = Field(ge=1, le=5)
    actionability_score: float = Field(ge=1, le=5)
    novelty_score: float = Field(ge=1, le=5)
    overall_score: float = Field(ge=1, le=5)
    notes: str = Field(default="", max_length=4000)

    @field_validator("reviewer", "rubric_version")
    @classmethod
    def strip_non_empty_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("notes")
    @classmethod
    def strip_notes(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def require_notes_for_changed_decisions(self) -> "HumanReviewPayload":
        if self.review_decision in {"adjust", "reject"} and not self.notes:
            raise ValueError("notes are required when adjusting or rejecting a review")
        return self


class HumanReviewCreate(HumanReviewPayload):
    evaluation_id: int = Field(gt=0)


class HumanReviewUpdate(HumanReviewPayload):
    pass


class HumanReviewRead(HumanReviewPayload):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: int
    evaluation_id: int
    scores_edited_after_reveal: bool
    created_at: datetime
    updated_at: datetime


class HumanReviewQueueItem(BaseModel):
    run_id: int
    evaluation_id: int
    workflow_name: str
    prompt_version: str
    model_name: str
    review_count: int
    created_at: datetime


class CalibrationDimension(BaseModel):
    dimension: str
    sample_count: int
    mae: float | None
    rmse: float | None
    bias: float | None
    judge_mean: float | None
    human_mean: float | None
    agreement_rate: float | None
    large_disagreement_rate: float | None
    overrating_rate: float | None
    underrating_rate: float | None
    correlation: float | None


class CalibrationDisagreement(BaseModel):
    run_id: int
    evaluation_id: int
    prompt_version: str
    evaluator_model: str
    judge_overall: float
    human_overall: float
    signed_delta: float
    absolute_delta: float
    decision: str
    review_date: datetime
    dangerous: bool


class CalibrationSummary(BaseModel):
    evaluator_model: str | None
    rubric_version: str | None
    review_count: int
    calibrated_evaluation_count: int
    reviewer_count: int
    evaluated_evaluation_count: int
    reviewed_evaluation_count: int
    evaluation_coverage_rate: float | None
    evaluated_run_count: int
    reviewed_run_count: int
    run_coverage_rate: float | None
    overall_mae: float | None
    overall_rmse: float | None
    overall_bias: float | None
    acceptance_rate: float | None
    overall_agreement_rate: float | None
    overall_large_disagreement_rate: float | None
    overall_correlation: float | None
    decision_counts: dict[str, int]
    dimensions: list[CalibrationDimension]
    disagreements: list[CalibrationDisagreement]
    dangerous_samples: list[CalibrationDisagreement]


class CalibrationScope(BaseModel):
    evaluator_model: str
    rubric_version: str
    review_count: int
