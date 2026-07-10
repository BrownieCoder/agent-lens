from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from .evaluation import EvaluationRead


class RunCreate(BaseModel):
    workflow_name: str = "x-signal-agent"
    source_type: str
    input_text: str
    output_text: str
    prompt_version: str
    model_name: str
    provider: str = "openai"
    token_input: int = Field(default=0, ge=0)
    token_output: int = Field(default=0, ge=0)
    estimated_cost: float = Field(default=0, ge=0)
    latency_ms: int = Field(default=0, ge=0)
    status: str = "success"
    error_message: str | None = None
    regression_case_id: int | None = None


class RunRead(RunCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    evaluations: list[EvaluationRead] = Field(default_factory=list)
