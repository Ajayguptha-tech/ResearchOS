from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int | None = None
    email: str | None = None
    name: str | None = None
    message: str = ""


class RegistrationResponse(BaseModel):
    message: str = "Account created successfully."
    email: str
    access_token: str
    token_type: str = "bearer"
    user_id: int | None = None


class MessageResponse(BaseModel):
    message: str
