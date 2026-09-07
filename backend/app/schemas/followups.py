from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


FollowUpStatus = Literal["pending", "completed", "snoozed"]
ReminderChannel = Literal["in_app", "email", "voice"]


class FollowUpCreate(BaseModel):
    project_id: int | None = None
    title: str = Field(..., min_length=3, max_length=255)
    message: str = Field(..., min_length=3)
    due_at: datetime | None = None
    priority: Literal["low", "medium", "high"] = "medium"


class FollowUpUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=255)
    message: str | None = Field(default=None, min_length=3)
    due_at: datetime | None = None
    priority: Literal["low", "medium", "high"] | None = None
    status: FollowUpStatus | None = None


class FollowUpResponse(BaseModel):
    id: int
    project_id: int | None
    title: str
    message: str
    due_at: datetime | None
    priority: str
    status: str
    snoozed_until: datetime | None
    completed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ReminderCreate(BaseModel):
    followup_id: int
    channel: ReminderChannel = "in_app"
    remind_at: datetime
    max_reminders: int = Field(default=3, ge=1, le=20)


class ReminderResponse(BaseModel):
    id: int
    followup_id: int
    channel: str
    remind_at: datetime
    enabled: bool
    attempts: int
    max_reminders: int
    last_error: str | None

    model_config = {"from_attributes": True}


class PreferenceUpdate(BaseModel):
    in_app_enabled: bool | None = None
    email_enabled: bool | None = None
    voice_enabled: bool | None = None
    phone_consent: bool | None = None
    quiet_start: str | None = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    quiet_end: str | None = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    timezone: str = "UTC"


class PreferenceResponse(PreferenceUpdate):
    id: int
    user_id: int

    model_config = {"from_attributes": True}
