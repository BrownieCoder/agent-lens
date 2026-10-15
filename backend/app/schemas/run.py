from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from .evaluation import EvaluationRead


class RunCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)
    workflow_name: str = Field(default="x-signal-agent", min_length=1, max_length=120)
    source_type: str = Field(min_length=1, max_length=80)
    input_text: str = Field(min_length=1, max_length=100000)
    output_text: str = Field(max_length=100000)
    prompt_version: str = Field(min_length=1, max_length=120)
    model_name: str = Field(min_length=1, max_length=120)
    provider: str = Field(default="openai", min_length=1, max_length=80)
    token_input: int | None = Field(default=None, ge=0, le=1000000000)
    token_output: int | None = Field(default=None, ge=0, le=1000000000)
    estimated_cost: float | None = Field(default=None, ge=0, le=1000000000)
    latency_ms: int | None = Field(default=None, ge=0, le=1000000000)
    status: Literal["success", "failed", "error"] = "success"
    error_message: str | None = Field(default=None, max_length=4000)
    regression_case_id: int | None = Field(default=None, gt=0)
    prompt_template_hash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    generation_parameters: dict[str, str | int | float | bool | None] | None = None
    dataset_name: str | None = Field(default=None, min_length=1, max_length=120)
    experiment_name: str | None = Field(default=None, min_length=1, max_length=120)

    @field_validator("generation_parameters")
    @classmethod
    def bounded_parameters(cls, value):
        import math
        if value is not None:
            if len(value) > 50 or any(len(key) > 120 or not key.strip() for key in value):
                raise ValueError("generation_parameters supports up to 50 nonblank keys of 120 characters")
            if any(isinstance(item, str) and len(item) > 2000 or isinstance(item, float) and not math.isfinite(item) for item in value.values()):
                raise ValueError("generation_parameters values must be finite and bounded")
        return value

    @field_validator("workflow_name", "source_type", "prompt_version", "model_name", "provider", "input_text")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

    @model_validator(mode="after")
    def successful_output(self):
        if self.status == "success" and not self.output_text.strip():
            raise ValueError("successful runs require nonblank output_text")
        return self


class RunRead(RunCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    usage_source: str = "caller-reported"
    legacy_usage: dict | None = None
    last_evaluation_error: str | None = None
    evaluations: list[EvaluationRead] = Field(default_factory=list)
