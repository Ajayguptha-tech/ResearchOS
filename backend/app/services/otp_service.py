"""OTP generation, hashing, and verification service.

Security properties:
- OTPs are 6-digit cryptographically random numbers.
- Only the SHA-256 hash is stored in the database.
- Verification has a maximum number of attempts.
- Resend operations have a cooldown period.
- OTPs expire after a configurable duration (default 10 minutes).
"""

from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.db.models import EmailVerification, PasswordResetToken, User

logger = logging.getLogger(__name__)

OTP_LENGTH = 6
OTP_EXPIRY_MINUTES = 10
OTP_MAX_ATTEMPTS = 5
OTP_RESEND_COOLDOWN_SECONDS = 60


def generate_otp() -> str:
    """Generate a cryptographically secure 6-digit OTP."""
    return f"{secrets.randbelow(10**OTP_LENGTH):0{OTP_LENGTH}d}"


def hash_otp(otp: str) -> str:
    """Hash an OTP using SHA-256."""
    return hashlib.sha256(otp.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Email Verification
# ---------------------------------------------------------------------------

def create_email_verification(
    db: Session,
    user_id: int,
    purpose: str = "registration",
) -> str:
    """Create a new email verification record and return the plaintext OTP.

    The plaintext OTP is returned ONLY to be sent via email.  It is never
    stored in the database.
    """
    # Invalidate any existing active OTPs for this user and purpose
    existing = (
        db.query(EmailVerification)
        .filter(
            EmailVerification.user_id == user_id,
            EmailVerification.purpose == purpose,
        )
        .all()
    )
    for record in existing:
        db.delete(record)

    otp = generate_otp()
    now = datetime.now(timezone.utc)

    verification = EmailVerification(
        user_id=user_id,
        otp_hash=hash_otp(otp),
        expires_at=now + timedelta(minutes=OTP_EXPIRY_MINUTES),
        purpose=purpose,
    )
    db.add(verification)
    db.commit()

    return otp


def verify_email_otp(
    db: Session,
    user_id: int,
    otp: str,
    purpose: str = "registration",
) -> tuple[bool, str]:
    """Verify an OTP for email verification.

    Returns (success, message).
    """
    now = datetime.now(timezone.utc)

    record = (
        db.query(EmailVerification)
        .filter(
            EmailVerification.user_id == user_id,
            EmailVerification.purpose == purpose,
        )
        .order_by(EmailVerification.created_at.desc())
        .first()
    )

    if not record:
        return False, "No verification code found. Please request a new one."

    # Check expiry
    if record.expires_at.replace(tzinfo=timezone.utc) < now:
        db.delete(record)
        db.commit()
        return False, "Verification code has expired. Please request a new one."

    # Check attempts
    if record.attempts >= OTP_MAX_ATTEMPTS:
        db.delete(record)
        db.commit()
        return False, "Too many failed attempts. Please request a new code."

    # Verify
    record.attempts += 1
    if record.otp_hash != hash_otp(otp):
        db.commit()
        remaining = OTP_MAX_ATTEMPTS - record.attempts
        return False, f"Invalid verification code. {remaining} attempt(s) remaining."

    # Success — delete the record and mark user as verified
    db.delete(record)
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.email_verified = True
    db.commit()

    return True, "Email verified successfully."


def can_resend_otp(db: Session, user_id: int, purpose: str = "registration") -> tuple[bool, str]:
    """Check whether the user is within the resend cooldown period."""
    now = datetime.now(timezone.utc)
    record = (
        db.query(EmailVerification)
        .filter(
            EmailVerification.user_id == user_id,
            EmailVerification.purpose == purpose,
        )
        .order_by(EmailVerification.created_at.desc())
        .first()
    )
    if not record:
        return True, ""

    elapsed = (now - record.created_at.replace(tzinfo=timezone.utc)).total_seconds()
    if elapsed < OTP_RESEND_COOLDOWN_SECONDS:
        remaining = int(OTP_RESEND_COOLDOWN_SECONDS - elapsed)
        return False, f"Please wait {remaining} second(s) before requesting a new code."

    return True, ""


# ---------------------------------------------------------------------------
# Password Reset
# ---------------------------------------------------------------------------

def create_password_reset_token(db: Session, user_id: int) -> str:
    """Create a password reset token and return the plaintext OTP."""
    # Invalidate existing tokens
    existing = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.user_id == user_id,
            PasswordResetToken.used.is_(False),
        )
        .all()
    )
    for record in existing:
        record.used = True

    otp = generate_otp()
    now = datetime.now(timezone.utc)

    token = PasswordResetToken(
        user_id=user_id,
        token_hash=hash_otp(otp),
        expires_at=now + timedelta(minutes=OTP_EXPIRY_MINUTES),
    )
    db.add(token)
    db.commit()

    return otp


def verify_password_reset_token(
    db: Session,
    user_id: int,
    otp: str,
    mark_used: bool = False,
    increment_attempts: bool = True,
) -> tuple[bool, str]:
    """Verify a password reset OTP.

    When *mark_used* is True the token is marked as used on success (for
    the final reset-password step).  For the intermediate verify-reset-otp
    step the caller passes mark_used=False AND increment_attempts=False so
    the token stays valid for the actual password change and doesn't burn
    an attempt.

    Returns (success, message).
    """
    now = datetime.now(timezone.utc)

    record = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.user_id == user_id,
            PasswordResetToken.used.is_(False),
        )
        .order_by(PasswordResetToken.created_at.desc())
        .first()
    )

    if not record:
        return False, "No reset code found. Please request a new one."

    if record.expires_at.replace(tzinfo=timezone.utc) < now:
        record.used = True
        db.commit()
        return False, "Reset code has expired. Please request a new one."

    if record.attempts >= OTP_MAX_ATTEMPTS:
        record.used = True
        db.commit()
        return False, "Too many failed attempts. Please request a new code."

    if increment_attempts:
        record.attempts += 1

    if record.token_hash != hash_otp(otp):
        db.commit()
        remaining = OTP_MAX_ATTEMPTS - record.attempts
        return False, f"Invalid reset code. {remaining} attempt(s) remaining."

    # Success
    if mark_used:
        record.used = True
    db.commit()
    return True, "Reset code verified successfully."


def can_resend_password_reset(db: Session, user_id: int) -> tuple[bool, str]:
    """Check cooldown for password reset resend."""
    now = datetime.now(timezone.utc)
    record = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.user_id == user_id,
            PasswordResetToken.used.is_(False),
        )
        .order_by(PasswordResetToken.created_at.desc())
        .first()
    )
    if not record:
        return True, ""

    elapsed = (now - record.created_at.replace(tzinfo=timezone.utc)).total_seconds()
    if elapsed < OTP_RESEND_COOLDOWN_SECONDS:
        remaining = int(OTP_RESEND_COOLDOWN_SECONDS - elapsed)
        return False, f"Please wait {remaining} second(s) before requesting a new code."

    return True, ""


def find_user_by_email(db: Session, email: str) -> User | None:
    """Find a user by email (normalized)."""
    return db.query(User).filter(User.email == email.strip().lower()).first()
