"""Comprehensive tests for OTP authentication, verification, cooldown, and forgot password flows."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.v1.routes import auth
from app.core.security import hash_password, verify_password
from app.db.models import EmailVerification, PasswordResetToken, User
from app.main import app
from app.services.otp_service import create_email_verification, create_password_reset_token_for_email
from conftest import TestingSessionLocal


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def clean_auth_tables(db_session):
    db_session.query(EmailVerification).delete()
    db_session.query(PasswordResetToken).delete()
    db_session.query(User).delete()
    db_session.commit()


@pytest.fixture
def client():
    return TestClient(app)


def test_registration_generates_single_otp_and_email(client, db_session, monkeypatch):
    """Registering an account should create exactly ONE OTP and send exactly ONE email."""
    mock_send = MagicMock(return_value={"status": "sent"})
    monkeypatch.setattr(auth, "send_email", mock_send)

    payload = {
        "email": "dr_curie@lab.edu",
        "password": "SecurePassword123!",
        "name": "Marie Curie",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["require_verification"] is True
    assert data["email"] == "dr_curie@lab.edu"
    # Ensure OTP is NEVER leaked in response
    assert "otp" not in data
    assert "code" not in data

    # Verify exactly 1 email was sent
    assert mock_send.call_count == 1
    call_args = mock_send.call_args[0]
    assert call_args[0] == "dr_curie@lab.edu"
    assert "Verification" in call_args[1]

    # Verify exactly 1 DB record exists
    otps = db_session.query(EmailVerification).all()
    assert len(otps) == 1
    assert otps[0].user_id is not None
    assert otps[0].expires_at > datetime.now(timezone.utc).replace(tzinfo=None)


def test_registration_rapid_duplicate_submits_do_not_send_multiple_emails(client, db_session, monkeypatch):
    """Immediate second register submit for unverified email should NOT send another email (cooldown protected)."""
    mock_send = MagicMock(return_value={"status": "sent"})
    monkeypatch.setattr(auth, "send_email", mock_send)

    payload = {
        "email": "pasteur@microbio.org",
        "password": "SecurePassword123!",
        "name": "Louis Pasteur",
    }
    res1 = client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201

    # Rapid second registration attempt
    res2 = client.post("/api/v1/auth/register", json=payload)
    assert res2.status_code == 201
    assert res2.json()["require_verification"] is True

    # Email must have been sent only once!
    assert mock_send.call_count == 1


def test_login_unverified_account_does_not_send_otp_email(client, db_session, monkeypatch):
    """CRITICAL: Logging in with unverified account must reject with 403 and NOT send unsolicited OTP email."""
    mock_send = MagicMock(return_value={"status": "sent"})
    monkeypatch.setattr(auth, "send_email", mock_send)

    # Register user first
    client.post(
        "/api/v1/auth/register",
        json={"email": "unverified@science.org", "password": "SecretPassword1!", "name": "Unverified"},
    )
    assert mock_send.call_count == 1

    # Reset mock count
    mock_send.reset_mock()

    # Attempt login without having verified
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "unverified@science.org", "password": "SecretPassword1!"},
    )
    assert login_res.status_code == 403
    assert "verify" in login_res.json()["detail"].lower()

    # MUST NOT send an email automatically on login!
    assert mock_send.call_count == 0


def test_otp_verification_success_and_consumption(client, db_session):
    """Entering the correct OTP verifies the account and consumes/deletes the token."""
    user = User(
        email="raman@physics.in",
        name="C.V. Raman",
        password_hash=hash_password("Password123!"),
        email_verified=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    otp = create_email_verification(db_session, user.id, purpose="registration")

    # Verify with correct OTP
    verify_res = client.post(
        "/api/v1/auth/verify-email",
        json={"email": "raman@physics.in", "otp": otp},
    )
    assert verify_res.status_code == 200
    assert "access_token" in verify_res.json()

    # User is now verified
    db_session.refresh(user)
    assert user.email_verified is True

    # Token has been consumed (deleted)
    remaining_tokens = db_session.query(EmailVerification).filter(EmailVerification.user_id == user.id).all()
    assert len(remaining_tokens) == 0

    # Second attempt with same OTP fails (cannot reuse)
    reuse_res = client.post(
        "/api/v1/auth/verify-email",
        json={"email": "raman@physics.in", "otp": otp},
    )
    assert reuse_res.status_code == 400


def test_otp_verification_wrong_code(client, db_session):
    """Entering wrong OTP fails with 400 and keeps account unverified."""
    user = User(
        email="bose@quantum.in",
        name="S.N. Bose",
        password_hash=hash_password("Password123!"),
        email_verified=False,
    )
    db_session.add(user)
    db_session.commit()

    create_email_verification(db_session, user.id, purpose="registration")

    bad_res = client.post(
        "/api/v1/auth/verify-email",
        json={"email": "bose@quantum.in", "otp": "999999"},
    )
    assert bad_res.status_code == 400
    assert "invalid" in bad_res.json()["detail"].lower()

    db_session.refresh(user)
    assert user.email_verified is False


def test_otp_verification_expired_code(client, db_session):
    """Entering an expired OTP fails with 400."""
    user = User(
        email="fermi@chicago.edu",
        name="Enrico Fermi",
        password_hash=hash_password("Password123!"),
        email_verified=False,
    )
    db_session.add(user)
    db_session.commit()

    otp = create_email_verification(db_session, user.id, purpose="registration")

    # Artificially expire the token in DB
    ev = db_session.query(EmailVerification).filter(EmailVerification.user_id == user.id).first()
    ev.expires_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=1)
    db_session.commit()

    expired_res = client.post(
        "/api/v1/auth/verify-email",
        json={"email": "fermi@chicago.edu", "otp": otp},
    )
    assert expired_res.status_code == 400
    assert "expired" in expired_res.json()["detail"].lower()


def test_resend_otp_enforces_60s_cooldown(client, db_session, monkeypatch):
    """Explicitly clicking Resend OTP immediately returns 429 cooldown error."""
    mock_send = MagicMock(return_value={"status": "sent"})
    monkeypatch.setattr(auth, "send_email", mock_send)

    user = User(
        email="feynman@caltech.edu",
        name="Richard Feynman",
        password_hash=hash_password("Password123!"),
        email_verified=False,
    )
    db_session.add(user)
    db_session.commit()

    # User has an OTP created right now
    create_email_verification(db_session, user.id, purpose="registration")

    # Press Resend OTP immediately: must return 429
    resend_res = client.post("/api/v1/auth/resend-otp", json={"email": "feynman@caltech.edu"})
    assert resend_res.status_code == 429
    assert "wait" in resend_res.json()["detail"].lower()
    assert mock_send.call_count == 0


def test_resend_otp_after_cooldown_generates_one_new_email(client, db_session, monkeypatch):
    """Explicitly clicking Resend OTP after 60s cooldown succeeds and sends exactly 1 new OTP email."""
    mock_send = MagicMock(return_value={"status": "sent"})
    monkeypatch.setattr(auth, "send_email", mock_send)

    user = User(
        email="oppie@ias.edu",
        name="J. Robert Oppenheimer",
        password_hash=hash_password("Password123!"),
        email_verified=False,
    )
    db_session.add(user)
    db_session.commit()

    old_otp = create_email_verification(db_session, user.id, purpose="registration")

    # Backdate created_at by 70 seconds
    ev = db_session.query(EmailVerification).filter(EmailVerification.user_id == user.id).first()
    ev.created_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=70)
    db_session.commit()

    # User clicks Resend OTP
    resend_res = client.post("/api/v1/auth/resend-otp", json={"email": "oppie@ias.edu"})
    assert resend_res.status_code == 200
    assert mock_send.call_count == 1

    # Verify a new OTP was created
    new_otps = db_session.query(EmailVerification).filter(EmailVerification.user_id == user.id).all()
    assert len(new_otps) == 1


def test_verified_user_cannot_resend_otp(client, db_session):
    """Already verified user cannot trigger resend OTP."""
    user = User(
        email="verified_scholar@oxford.ac.uk",
        name="Verified Scholar",
        password_hash=hash_password("Password123!"),
        email_verified=True,
    )
    db_session.add(user)
    db_session.commit()

    res = client.post("/api/v1/auth/resend-otp", json={"email": "verified_scholar@oxford.ac.uk"})
    assert res.status_code == 400
    assert "already verified" in res.json()["detail"].lower()


def test_forgot_password_and_reset_flow(client, db_session, monkeypatch):
    """Forgot password sends single email, verifies OTP, and resets password, invalidating the token."""
    mock_send = MagicMock(return_value={"status": "sent"})
    monkeypatch.setattr(auth, "send_email", mock_send)

    user = User(
        email="turing@bletchley.uk",
        name="Alan Turing",
        password_hash=hash_password("OldPassword123!"),
        email_verified=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # 1. Request password reset
    forgot_res = client.post("/api/v1/auth/forgot-password", json={"email": "turing@bletchley.uk"})
    assert forgot_res.status_code == 200
    assert mock_send.call_count == 1

    # Cooldown on immediate second request
    forgot_res2 = client.post("/api/v1/auth/forgot-password", json={"email": "turing@bletchley.uk"})
    assert forgot_res2.status_code == 429

    # Generate a known reset OTP for test verification
    # Retrieve the reset OTP from the first call or generate via service
    # The first call created one; let's backdate created_at to bypass cooldown and get an OTP
    db_session.query(PasswordResetToken).delete()
    db_session.commit()
    otp, _ = create_password_reset_token_for_email(db_session, "turing@bletchley.uk")

    # 2. Verify reset OTP
    verify_reset_res = client.post(
        "/api/v1/auth/verify-reset-otp",
        json={"email": "turing@bletchley.uk", "otp": otp},
    )
    assert verify_reset_res.status_code == 200

    # 3. Reset password using valid otp
    reset_pw_res = client.post(
        "/api/v1/auth/reset-password",
        json={
            "email": "turing@bletchley.uk",
            "otp": otp,
            "new_password": "NewSecurePassword456!",
        },
    )
    assert reset_pw_res.status_code == 200

    # 4. Attempting to reuse same OTP fails (it was marked used)
    reuse_res = client.post(
        "/api/v1/auth/reset-password",
        json={
            "email": "turing@bletchley.uk",
            "otp": otp,
            "new_password": "AnotherPassword789!",
        },
    )
    assert reuse_res.status_code == 400

    # 5. Verify user can log in with new password
    db_session.refresh(user)
    assert verify_password("NewSecurePassword456!", user.password_hash)
    assert not verify_password("OldPassword123!", user.password_hash)
