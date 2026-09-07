from pydantic import BaseModel, Field


class SuccessResponse(BaseModel):
    success: bool = True
    message: str = "ok"


class ErrorResponse(BaseModel):
    success: bool = False
    message: str = Field(..., min_length=1)
