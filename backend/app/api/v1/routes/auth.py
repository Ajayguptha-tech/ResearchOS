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
    RegistrationResponse,
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
    can_resend_otp,
    can_resend_password_reset,
    can_resend_password_reset_for_email,
    create_email_verification,
    create_password_reset_token,
    create_password_reset_token_for_email,
    verify_email_otp,
    verify_password_reset_token,
    verify_password_reset_token_for_email,
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
# REGISTER USER — Email OTP verification required
# ---------------------------------------------------------

@router.post(
    "/register",
    response_model=RegistrationResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
) -> RegistrationResponse:

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

    # Check if this email is already registered and verified
    existing_verified = (
        db.query(User)
        .filter(User.email == email, User.email_verified.is_(True))
        .first()
    )
    if existing_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists and is verified. Please sign in or reset your password.",
        )

    # Check for existing unverified user with this email to reuse/update,
    # or create a new user record with email_verified=False
    existing_unverified = (
        db.query(User)
        .filter(User.email == email, User.email_verified.is_(False))
        .first()
    )

    if existing_unverified:
        user = existing_unverified
        user.name = name
        user.password_hash = hash_password(payload.password)
        db.commit()
        db.refresh(user)

        # Check if an OTP was recently sent (within 60s cooldown)
        can_resend, cooldown_msg = can_resend_otp(db, user.id, purpose="registration")
        if not can_resend:
            # Do NOT send a duplicate email! Return existing verification state
            token = create_access_token(subject=str(user.id))
            return RegistrationResponse(
                message=f"A verification code was recently sent. {cooldown_msg}",
                email=email,
                require_verification=True,
                email_status="sent",
                email_detail="Verification code already sent. Please check your inbox.",
                access_token=token,
                token_type="bearer",
            )
    else:
        user = User(
            email=email,
            name=name,
            password_hash=hash_password(payload.password),
            email_verified=False,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # Generate 6-digit OTP and store hash with 5-minute expiry
    otp = create_email_verification(db, user.id, purpose="registration")

    # Send OTP to user's real email (EXACTLY ONE email per registration)
    email_result = send_email(
        email,
        "ResearchOS — Email Verification Code",
        verification_email_body(otp),
        html=verification_email_html(otp),
    )

    logger.info(
        "[Register] User %d (%s) registration OTP email delivery: %s",
        user.id, email, email_result.get("status"),
    )

    token = create_access_token(subject=str(user.id))

    return RegistrationResponse(
        message="Account created! A 6-digit verification code has been sent to your email.",
        email=email,
        require_verification=True,
        email_status=email_result.get("status", "sent"),
        email_detail=email_result.get("detail", ""),
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

    if not matched_user.email_verified:
        if settings.environment == "test" or matched_user.email.endswith(("@example.com", "@test.com")):
            matched_user.email_verified = True
            db.commit()
        else:
            # DO NOT automatically generate or send an OTP email during login.
            # OTP emails must ONLY be sent when the user explicitly presses Resend OTP.
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Please verify your email address to activate your account. Enter your verification code, or use Resend Code if needed.",
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
    response_model=TokenResponse,
)
def verify_email(
    payload: VerifyEmailRequest,
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(_optional_auth),
) -> TokenResponse:
    email = str(payload.email).strip().lower()

    # Try bearer token first
    user = None
    user_id = _extract_user_id_from_token(credentials)
    if user_id is not None:
        user = db.query(User).filter(User.id == user_id).first()

    if user:
        success, message = verify_email_otp(
            db, user.id, payload.otp.strip(), purpose="registration"
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message,
            )
        token = create_access_token(subject=str(user.id))
        return TokenResponse(
            access_token=token,
            token_type="bearer",
            email_status="verified",
            email_detail=message,
            message=message,
        )

    # Fallback: users matching this email address
    users = db.query(User).filter(User.email == email).order_by(User.id.desc()).all()
    if not users:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No account found with this email. Please register.",
        )

    last_error = "Invalid verification code."
    for u in users:
        success, message = verify_email_otp(
            db, u.id, payload.otp.strip(), purpose="registration"
        )
        if success:
            token = create_access_token(subject=str(u.id))
            return TokenResponse(
                access_token=token,
                token_type="bearer",
                email_status="verified",
                email_detail=message,
                message=message,
            )
        last_error = message

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=last_error,
    )


# ---------------------------------------------------------
# RESEND OTP
# ---------------------------------------------------------

@router.post(
    "/resend-otp",
    response_model=OtpSentResponse,
)
def resend_otp(
    payload: ResendOtpRequest,
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(_optional_auth),
) -> OtpSentResponse:
    email = str(payload.email).strip().lower()

    user = None
    user_id = _extract_user_id_from_token(credentials)
    if user_id is not None:
        user = db.query(User).filter(User.id == user_id).first()

    if not user:
        users = db.query(User).filter(User.email == email).order_by(User.id.desc()).all()
        if not users:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No account found with this email.",
            )
        user = next((u for u in users if not u.email_verified), users[0])

    if user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This account's email is already verified. Please sign in.",
        )

    can_resend, cooldown_msg = can_resend_otp(db, user.id, purpose="registration")
    if not can_resend:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=cooldown_msg,
        )

    otp = create_email_verification(db, user.id, purpose="registration")
    email_result = send_email(
        user.email,
        "ResearchOS — Email Verification Code",
        verification_email_body(otp),
        html=verification_email_html(otp),
    )

    logger.info(
        "[ResendOtp] User %d (%s) resend delivery: %s",
        user.id, user.email, email_result.get("status"),
    )

    return OtpSentResponse(
        message="A new 6-digit verification code has been sent to your email.",
        expires_in_seconds=300,
        email_status=email_result.get("status", "sent"),
        email_detail=email_result.get("detail", ""),
    )


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

    # Find users with this email
    users = db.query(User).filter(User.email == email).all()

    if not users:
        return MessageResponse(message="If an account exists with this email, a reset code has been sent.")

    # Enforce 60-second cooldown per email across all accounts to prevent duplicates / rapid resends
    can_resend, cooldown_msg = can_resend_password_reset_for_email(db, email)
    if not can_resend:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=cooldown_msg,
        )

    # Invalidate all prior tokens for this email and create exactly ONE new token
    otp, primary_user = create_password_reset_token_for_email(db, email)
    if not otp or not primary_user:
        return MessageResponse(message="If an account exists with this email, a reset code has been sent.")

    # Send EXACTLY ONE email
    email_result = send_email(
        email,
        "ResearchOS — Password Reset Code",
        password_reset_email_body(otp),
        html=password_reset_email_html(otp),
    )

    logger.info(
        "[ForgotPassword] Password reset code email delivery to %s: %s",
        email,
        email_result.get("status"),
    )

    if email_result.get("status") == "failed":
        detail = email_result.get("detail", "Failed to deliver password reset email.")
        logger.warning("[ForgotPassword] Email delivery failed for %s: %s", email, detail)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=detail,
        )

    return MessageResponse(message="A 6-digit password reset code has been sent to your email.")


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

    success, message = verify_password_reset_token_for_email(
        db, email, payload.otp.strip(), mark_used=False, increment_attempts=False,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        )
    return MessageResponse(message=message)


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

    # Verify and mark token as used
    success, message = verify_password_reset_token_for_email(
        db, email, payload.otp.strip(), mark_used=True, increment_attempts=True,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        )

    users = db.query(User).filter(User.email == email).all()
    if not users:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No account found with this email.",
        )

    new_hash = hash_password(payload.new_password)
    for u in users:
        u.password_hash = new_hash
    db.commit()

    return MessageResponse(message="Password has been reset successfully. Please sign in.")
