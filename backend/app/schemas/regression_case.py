from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RegressionCaseCreate(BaseModel):
    name: str
    input_text: str
    expected_focus: str
    notes: str | None = None


class RegressionCaseRead(RegressionCaseCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
