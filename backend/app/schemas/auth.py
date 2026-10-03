from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)


class ResendOtpRequest(BaseModel):
    email: EmailStr


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class VerifyResetOtpRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=8, max_length=128)


class MessageResponse(BaseModel):
    message: str


class OtpSentResponse(BaseModel):
    message: str
    expires_in_seconds: int = 300
    email_status: str = "sent"
    email_detail: str = ""


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    email_status: str = ""
    email_detail: str = ""
    message: str = ""


class RegistrationResponse(BaseModel):
    message: str = "Verification code sent to your email."
    email: str
    require_verification: bool = True
    email_status: str = "sent"
    email_detail: str = ""
    access_token: str = ""
    token_type: str = "bearer"
