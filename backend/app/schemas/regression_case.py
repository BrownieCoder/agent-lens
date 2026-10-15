from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, ValidationInfo


class RegressionCaseCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    name: str = Field(min_length=1, max_length=160)
    input_text: str = Field(min_length=1, max_length=100000)
    expected_focus: str = Field(min_length=1, max_length=100000)
    notes: str | None = Field(default=None, max_length=4000)

    @field_validator("name", "input_text", "expected_focus")
    @classmethod
    def nonblank(cls, value: str, info: ValidationInfo) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value.strip() if info.field_name == "name" else value


class RegressionCaseRead(RegressionCaseCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
