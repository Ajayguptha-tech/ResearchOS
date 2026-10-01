"""Authentication routes.

Registration creates the user immediately (no email OTP verification).
Login authenticates by email + password, trying all accounts that share
the same email.  Duplicate emails are intentionally supported.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_db
from app.core.security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.db.models import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    MessageResponse,
    OtpSentResponse,
    ResetPasswordRequest,
    ResendOtpRequest,
    TokenResponse,
    VerifyEmailRequest,
    VerifyResetOtpRequest,
)
from app.services.email_service import (
    password_reset_email_body,
    password_reset_email_html,
    send_email,
    verification_email_body,
    verification_email_html,
)
from app.services.otp_service import (
    can_resend_password_reset,
    create_password_reset_token,
    verify_password_reset_token,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Optional bearer auth — used to identify the specific user when multiple
# accounts share the same email address.
_optional_auth = HTTPBearer(auto_error=False)


def _extract_user_id_from_token(credentials: HTTPAuthorizationCredentials | None) -> int | None:
    """Safely extract user_id from a bearer token. Returns None on failure."""
    if credentials is None:
        return None
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        sub = payload.get("sub")
        if sub is not None:
            return int(sub)
    except (JWTError, TypeError, ValueError):
        pass
    return None


# ---------------------------------------------------------
# REGISTER
# ---------------------------------------------------------

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(
        min_length=8,
        max_length=128,
    )
    name: str = Field(
        min_length=2,
        max_length=100,
    )


# ---------------------------------------------------------
# LOGIN
# ---------------------------------------------------------

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(
        min_length=1,
        max_length=128,
    )


# ---------------------------------------------------------
# REGISTER USER — no OTP, no email verification required
# ---------------------------------------------------------

@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:

    email = str(payload.email).strip().lower()
    name = payload.name.strip()

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is required.",
        )

    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Name is required.",
        )

    # Create user — email_verified is True by default (no OTP required)
    user = User(
        email=email,
        name=name,
        password_hash=hash_password(payload.password),
        email_verified=True,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    # Log the user in immediately
    token = create_access_token(subject=str(user.id))

    return TokenResponse(
        access_token=token,
        token_type="bearer",
    )


# ---------------------------------------------------------
# LOGIN USER — supports multiple accounts per email
# ---------------------------------------------------------

@router.post(
    "/login",
    response_model=TokenResponse,
)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:

    email = str(payload.email).strip().lower()

    # Find ALL users with this email (supports duplicate emails)
    users = db.query(User).filter(User.email == email).all()

    if not users:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    # Try each account's password
    matched_user = None
    for user in users:
        if verify_password(payload.password, user.password_hash):
            matched_user = user
            break

    if not matched_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    token = create_access_token(subject=str(matched_user.id))

    return TokenResponse(
        access_token=token,
        token_type="bearer",
    )


# ---------------------------------------------------------
# CURRENT USER
# ---------------------------------------------------------

@router.get("/me")
def me(
    user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str | int | bool]:

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
        )

    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "email_verified": user.email_verified,
    }


# ---------------------------------------------------------
# VERIFY EMAIL — kept as a no-op for backwards compatibility
# ---------------------------------------------------------

# ---------------------------------------------------------
# SMTP STATUS — truthful diagnostic (never exposes the password)
# ---------------------------------------------------------

@router.get("/smtp-status")
def smtp_status() -> dict:
    """Return SMTP connectivity/authentication status for the configured provider.

    This runs a real connect + authenticate probe (no email is sent).
    The response never includes the SMTP password.
    """
    from app.services.email_service import test_smtp_connection

    return test_smtp_connection()


@router.post(
    "/verify-email",
    response_model=MessageResponse,
)
def verify_email(
    payload: VerifyEmailRequest,
    db: Session = Depends(get_db),
) -> MessageResponse:
    """No-op. Email verification is not required."""
    return MessageResponse(message="Email verification is not required.")


# ---------------------------------------------------------
# RESEND OTP — kept as a no-op for backwards compatibility
# ---------------------------------------------------------

@router.post(
    "/resend-otp",
    response_model=OtpSentResponse,
)
def resend_otp(
    payload: ResendOtpRequest,
    db: Session = Depends(get_db),
) -> OtpSentResponse:
    """No-op. Email verification is not required."""
    return OtpSentResponse(message="Email verification is not required.")


# ---------------------------------------------------------
# FORGOT PASSWORD
# ---------------------------------------------------------

@router.post(
    "/forgot-password",
    response_model=MessageResponse,
)
def forgot_password(
    payload: ForgotPasswordRequest,
    db: Session = Depends(get_db),
) -> MessageResponse:
    email = str(payload.email).strip().lower()

    # Find ALL users with this email (duplicate email support)
    users = db.query(User).filter(User.email == email).all()

    if not users:
        return MessageResponse(message="If an account exists with this email, a reset code has been sent.")

    # Send reset OTP to each account that isn't in cooldown
    for user in users:
        can_resend, cooldown_msg = can_resend_password_reset(db, user.id)
        if not can_resend:
            logger.info("[ForgotPassword] User %d (%s) in cooldown, skipping", user.id, email)
            continue

        otp = create_password_reset_token(db, user.id)
        email_result = send_email(
            email,
            "ResearchOS - Password Reset Code",
            password_reset_email_body(otp),
            html=password_reset_email_html(otp),
        )

        logger.info(
            "[ForgotPassword] Email delivery status for user %d (%s): %s",
            user.id, email, email_result.get("status"),
        )

    return MessageResponse(message="If an account exists with this email, a reset code has been sent.")


# ---------------------------------------------------------
# VERIFY RESET OTP
# ---------------------------------------------------------

@router.post(
    "/verify-reset-otp",
    response_model=MessageResponse,
)
def verify_reset_otp(
    payload: VerifyResetOtpRequest,
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(_optional_auth),
) -> MessageResponse:
    email = str(payload.email).strip().lower()

    # Try to identify the specific user from the access token
    user = None
    user_id = _extract_user_id_from_token(credentials)
    if user_id is not None:
        user = db.query(User).filter(User.id == user_id).first()

    if user:
        success, message = verify_password_reset_token(
            db, user.id, payload.otp, mark_used=False, increment_attempts=False,
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message,
            )
        return MessageResponse(message=message)

    # Fallback: try all users with this email
    users = db.query(User).filter(User.email == email).all()
    for u in users:
        success, message = verify_password_reset_token(
            db, u.id, payload.otp, mark_used=False, increment_attempts=False,
        )
        if success:
            return MessageResponse(message=message)

    return MessageResponse(message="If an account exists with this email, a reset code was sent.")


# ---------------------------------------------------------
# RESET PASSWORD
# ---------------------------------------------------------

@router.post(
    "/reset-password",
    response_model=MessageResponse,
)
def reset_password(
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(_optional_auth),
) -> MessageResponse:
    email = str(payload.email).strip().lower()

    # Try to identify the specific user from the access token
    user = None
    user_id = _extract_user_id_from_token(credentials)
    if user_id is not None:
        user = db.query(User).filter(User.id == user_id).first()

    if user:
        success, message = verify_password_reset_token(
            db, user.id, payload.otp, mark_used=True,
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message,
            )
        user.password_hash = hash_password(payload.new_password)
        db.commit()
        return MessageResponse(message="Password has been reset successfully. Please sign in.")

    # Fallback: try all users with this email
    users = db.query(User).filter(User.email == email).all()
    for u in users:
        success, message = verify_password_reset_token(
            db, u.id, payload.otp, mark_used=True,
        )
        if success:
            u.password_hash = hash_password(payload.new_password)
            db.commit()
            return MessageResponse(message="Password has been reset successfully. Please sign in.")

    return MessageResponse(message="If an account exists with this email, the password has been reset.")
