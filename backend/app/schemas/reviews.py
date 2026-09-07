from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


Decision = Literal["approved", "rejected", "changes_requested"]


class FeedbackCreate(BaseModel):
    decision: Decision
    message: str = Field(..., min_length=3)


class FeedbackResponse(BaseModel):
    id: int
    project_id: int
    reviewer_id: int
    decision: Decision
    message: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationResponse(BaseModel):
    id: int
    type: str
    message: str
    read_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
