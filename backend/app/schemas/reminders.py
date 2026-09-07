from datetime import datetime

from pydantic import BaseModel, Field


class ReminderCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    reminder_datetime: datetime


class ReminderUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    reminder_datetime: datetime | None = None


class ReminderResponse(BaseModel):
    id: int
    user_id: int
    title: str
    description: str | None
    reminder_datetime: datetime
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
