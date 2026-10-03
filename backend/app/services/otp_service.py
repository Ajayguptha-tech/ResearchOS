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
OTP_EXPIRY_MINUTES = 5
OTP_MAX_ATTEMPTS = 5
OTP_RESEND_COOLDOWN_SECONDS = 60


def _normalize_utc(dt: datetime) -> datetime:
    """Ensure datetime has timezone.utc."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


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
    now_naive = now.replace(tzinfo=None)

    verification = EmailVerification(
        user_id=user_id,
        otp_hash=hash_otp(otp),
        expires_at=now_naive + timedelta(minutes=OTP_EXPIRY_MINUTES),
        purpose=purpose,
        created_at=now_naive,
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
    if _normalize_utc(record.expires_at) < now:
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

    elapsed = (now - _normalize_utc(record.created_at)).total_seconds()
    if elapsed < OTP_RESEND_COOLDOWN_SECONDS:
        remaining = int(OTP_RESEND_COOLDOWN_SECONDS - elapsed)
        return False, f"Please wait {max(1, remaining)} second(s) before requesting a new code."

    return True, ""


def can_resend_otp_for_email(db: Session, email: str, purpose: str = "registration") -> tuple[bool, str]:
    """Check cooldown for registration OTP resend across all accounts with this email."""
    norm_email = email.strip().lower()
    user_ids = [u[0] for u in db.query(User.id).filter(User.email == norm_email).all()]
    if not user_ids:
        return True, ""

    now = datetime.now(timezone.utc)
    record = (
        db.query(EmailVerification)
        .filter(
            EmailVerification.user_id.in_(user_ids),
            EmailVerification.purpose == purpose,
        )
        .order_by(EmailVerification.created_at.desc())
        .first()
    )
    if not record:
        return True, ""

    elapsed = (now - _normalize_utc(record.created_at)).total_seconds()
    if elapsed < OTP_RESEND_COOLDOWN_SECONDS:
        remaining = int(OTP_RESEND_COOLDOWN_SECONDS - elapsed)
        return False, f"Please wait {max(1, remaining)} second(s) before requesting a new code."

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
    now_naive = now.replace(tzinfo=None)

    token = PasswordResetToken(
        user_id=user_id,
        token_hash=hash_otp(otp),
        expires_at=now_naive + timedelta(minutes=OTP_EXPIRY_MINUTES),
        created_at=now_naive,
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

    if _normalize_utc(record.expires_at) < now:
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
        if not increment_attempts:
            record.attempts += 1
        db.commit()
        remaining = max(0, OTP_MAX_ATTEMPTS - record.attempts)
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
        )
        .order_by(PasswordResetToken.created_at.desc())
        .first()
    )
    if not record:
        return True, ""

    elapsed = (now - _normalize_utc(record.created_at)).total_seconds()
    if elapsed < OTP_RESEND_COOLDOWN_SECONDS:
        remaining = int(OTP_RESEND_COOLDOWN_SECONDS - elapsed)
        return False, f"Please wait {max(1, remaining)} second(s) before requesting a new code."

    return True, ""


def can_resend_password_reset_for_email(db: Session, email: str) -> tuple[bool, str]:
    """Check cooldown for password reset resend across all accounts with this email."""
    norm_email = email.strip().lower()
    user_ids = [u[0] for u in db.query(User.id).filter(User.email == norm_email).all()]
    if not user_ids:
        return True, ""

    now = datetime.now(timezone.utc)
    # Check the most recently created token across ANY account with this email (used or unused)
    record = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.user_id.in_(user_ids))
        .order_by(PasswordResetToken.created_at.desc())
        .first()
    )
    if not record:
        return True, ""

    elapsed = (now - _normalize_utc(record.created_at)).total_seconds()
    if elapsed < OTP_RESEND_COOLDOWN_SECONDS:
        remaining = int(OTP_RESEND_COOLDOWN_SECONDS - elapsed)
        return False, f"Please wait {max(1, remaining)} second(s) before requesting a new code."

    return True, ""


def create_password_reset_token_for_email(db: Session, email: str) -> tuple[str, User] | tuple[None, None]:
    """Invalidate all previous tokens for accounts with this email and create exactly ONE new OTP."""
    norm_email = email.strip().lower()
    users = db.query(User).filter(User.email == norm_email).order_by(User.id.asc()).all()
    if not users:
        return None, None

    user_ids = [u.id for u in users]

    # Invalidate ALL existing active/unused tokens for all accounts sharing this email
    existing = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.user_id.in_(user_ids),
            PasswordResetToken.used.is_(False),
        )
        .all()
    )
    for record in existing:
        record.used = True

    # Associate new token with the primary user
    primary_user = users[0]
    otp = generate_otp()
    now = datetime.now(timezone.utc)
    now_naive = now.replace(tzinfo=None)

    token = PasswordResetToken(
        user_id=primary_user.id,
        token_hash=hash_otp(otp),
        expires_at=now_naive + timedelta(minutes=OTP_EXPIRY_MINUTES),
        created_at=now_naive,
    )
    db.add(token)
    db.commit()

    return otp, primary_user


def verify_password_reset_token_for_email(
    db: Session,
    email: str,
    otp: str,
    mark_used: bool = False,
    increment_attempts: bool = True,
) -> tuple[bool, str]:
    """Verify password reset OTP across accounts matching this email."""
    norm_email = email.strip().lower()
    user_ids = [u[0] for u in db.query(User.id).filter(User.email == norm_email).all()]
    if not user_ids:
        return False, "No reset code found. Please request a new one."

    now = datetime.now(timezone.utc)

    # Find the latest unused token for this email
    record = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.user_id.in_(user_ids),
            PasswordResetToken.used.is_(False),
        )
        .order_by(PasswordResetToken.created_at.desc())
        .first()
    )

    if not record:
        return False, "No reset code found. Please request a new one."

    if _normalize_utc(record.expires_at) < now:
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
        if not increment_attempts:
            record.attempts += 1
        db.commit()
        remaining = max(0, OTP_MAX_ATTEMPTS - record.attempts)
        return False, f"Invalid reset code. {remaining} attempt(s) remaining."

    # Success
    if mark_used:
        record.used = True
    db.commit()
    return True, "Reset code verified successfully."


def find_user_by_email(db: Session, email: str) -> User | None:
    """Find a user by email (normalized)."""
    return db.query(User).filter(User.email == email.strip().lower()).first()
