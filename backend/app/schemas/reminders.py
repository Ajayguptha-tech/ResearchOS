from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_serializer


class ReminderCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    reminder_datetime: datetime | str
    timezone: str = "Asia/Kolkata"


class ReminderUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    reminder_datetime: datetime | str | None = None
    timezone: str | None = None
    status: str | None = None


class ReminderResponse(BaseModel):
    id: int
    user_id: int
    title: str
    description: str | None
    reminder_datetime: datetime
    timezone: str = "Asia/Kolkata"
    status: str
    email_sent: bool = False
    email_sent_at: datetime | None = None
    last_error: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @field_serializer("reminder_datetime", "email_sent_at", "created_at", "updated_at")
    def serialize_dt(self, dt: datetime | None) -> str | None:
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
