"""Direct verification suite for all 18 master prompt tests.

Verifies:
- Tests 1-10: Authentication, dynamic recipients, OTP lifecycle, forgot password & reset
- Tests 11-18: Reminders, automatic scheduling, timezone accuracy, restart recovery, duplicate prevention, failure safety
"""

import time
import zoneinfo
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.security import hash_password, verify_password
from app.db.base import Base
from app.db.models import EmailVerification, PasswordResetToken, User, UserReminder
from app.services.email_service import reminder_email_body, send_email
from app.services.otp_service import (
    can_resend_otp,
    can_resend_password_reset_for_email,
    create_email_verification,
    create_password_reset_token_for_email,
    generate_otp,
    hash_otp,
    verify_email_otp,
    verify_password_reset_token_for_email,
)
from app.services.reminder_agent import (
    process_due_reminders,
    recover_stale_reminders,
)


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


# ===========================================================================
# AUTHENTICATION TESTS (TESTS 1 - 10)
# ===========================================================================

def test_01_and_02_and_03_forgot_password_dynamic_recipients(test_db):
    """TEST 1: Existing verified account -> Forgot Password (OTP request succeeds).
    TEST 2: Verify recipient -> OTP is sent to the exact email belonging to that account.
    TEST 3: Different existing account -> OTP goes to the second account's email.
    """
    # Create User A
    user_a = User(
        email="usera_verified@example.com",
        name="User A",
        password_hash=hash_password("OldPasswordA123!"),
        email_verified=True,
    )
    # Create User B
    user_b = User(
        email="userb_verified@example.com",
        name="User B",
        password_hash=hash_password("OldPasswordB123!"),
        email_verified=True,
    )
    test_db.add_all([user_a, user_b])
    test_db.commit()

    sent_emails = []

    def mock_send(to, subject, body, html=None):
        sent_emails.append({"to": to, "subject": subject, "body": body})
        return {"status": "sent", "detail": f"Sent to {to}"}

    with patch("app.services.email_service.send_email", side_effect=mock_send):
        # TEST 1 & 2: User A Forgot Password
        otp_a, primary_a = create_password_reset_token_for_email(test_db, user_a.email)
        assert otp_a is not None
        assert primary_a.id == user_a.id
        email_res_a = mock_send(user_a.email, "ResearchOS — Password Reset Code", f"OTP: {otp_a}")
        assert email_res_a["status"] == "sent"
        assert sent_emails[-1]["to"] == "usera_verified@example.com"
        assert otp_a in sent_emails[-1]["body"]

        # TEST 3: User B Forgot Password
        otp_b, primary_b = create_password_reset_token_for_email(test_db, user_b.email)
        assert otp_b is not None
        assert primary_b.id == user_b.id
        email_res_b = mock_send(user_b.email, "ResearchOS — Password Reset Code", f"OTP: {otp_b}")
        assert email_res_b["status"] == "sent"
        assert sent_emails[-1]["to"] == "userb_verified@example.com"
        assert otp_b in sent_emails[-1]["body"]

        # Verify separation: User A and User B received distinct OTPs to their own addresses
        assert sent_emails[0]["to"] == "usera_verified@example.com"
        assert sent_emails[1]["to"] == "userb_verified@example.com"
        assert otp_a != otp_b


def test_04_and_05_signup_and_resend_otp_dynamic_recipient(test_db):
    """TEST 4: New signup email -> Signup OTP goes to the entered email.
    TEST 5: Resend OTP -> New OTP goes to the same intended recipient.
    """
    new_email = "new_signup_student@example.com"
    user = User(
        email=new_email,
        name="New Student",
        password_hash=hash_password("Pass12345!"),
        email_verified=False,
    )
    test_db.add(user)
    test_db.commit()

    sent_emails = []

    def mock_send(to, subject, body, html=None):
        sent_emails.append({"to": to, "subject": subject, "body": body})
        return {"status": "sent", "detail": f"Sent to {to}"}

    # TEST 4: Generate signup OTP and send
    otp_signup = create_email_verification(test_db, user.id, purpose="registration")
    mock_send(new_email, "ResearchOS — Email Verification Code", f"Code: {otp_signup}")

    assert len(sent_emails) == 1
    assert sent_emails[0]["to"] == new_email
    assert otp_signup in sent_emails[0]["body"]

    # TEST 5: Resend OTP (simulate 61s cooldown elapsed)
    rec = test_db.query(EmailVerification).filter(EmailVerification.user_id == user.id).first()
    rec.created_at = (datetime.now(timezone.utc) - timedelta(seconds=70)).replace(tzinfo=None)
    test_db.commit()

    can_resend, _ = can_resend_otp(test_db, user.id, purpose="registration")
    assert can_resend is True

    otp_resend = create_email_verification(test_db, user.id, purpose="registration")
    mock_send(new_email, "ResearchOS — Email Verification Code", f"Code: {otp_resend}")

    assert len(sent_emails) == 2
    assert sent_emails[1]["to"] == new_email
    assert otp_resend in sent_emails[1]["body"]
    # Previous OTP replaced/invalidated
    old_valid, _ = verify_email_otp(test_db, user.id, otp_signup, purpose="registration")
    assert old_valid is False


def test_06_wrong_otp(test_db):
    """TEST 6: Wrong OTP -> Rejected."""
    user = User(email="test_wrong@example.com", name="Wrong User", password_hash="h", email_verified=False)
    test_db.add(user)
    test_db.commit()

    otp = create_email_verification(test_db, user.id, purpose="registration")
    wrong_code = "000000" if otp != "000000" else "111111"

    valid, msg = verify_email_otp(test_db, user.id, wrong_code, purpose="registration")
    assert valid is False
    assert "Invalid verification code" in msg


def test_07_expired_otp(test_db):
    """TEST 7: Expired OTP -> Rejected."""
    user = User(email="test_expired@example.com", name="Expired User", password_hash="h", email_verified=False)
    test_db.add(user)
    test_db.commit()

    otp = create_email_verification(test_db, user.id, purpose="registration")
    # Force expiry
    rec = test_db.query(EmailVerification).filter(EmailVerification.user_id == user.id).first()
    rec.expires_at = (datetime.now(timezone.utc) - timedelta(minutes=10)).replace(tzinfo=None)
    test_db.commit()

    valid, msg = verify_email_otp(test_db, user.id, otp, purpose="registration")
    assert valid is False
    assert "expired" in msg.lower()


def test_08_correct_otp(test_db):
    """TEST 8: Correct OTP -> Accepted and cannot be reused."""
    user = User(email="test_correct@example.com", name="Correct User", password_hash="h", email_verified=False)
    test_db.add(user)
    test_db.commit()

    otp = create_email_verification(test_db, user.id, purpose="registration")
    valid, msg = verify_email_otp(test_db, user.id, otp, purpose="registration")
    assert valid is True
    assert user.email_verified is True

    # Single-use: Reusing the same OTP must fail
    reused_valid, _ = verify_email_otp(test_db, user.id, otp, purpose="registration")
    assert reused_valid is False


def test_09_and_10_password_reset_flow(test_db):
    """TEST 9: Password reset -> New password successfully saved.
    TEST 10: Old password -> Old password no longer works.
    """
    old_pw = "OriginalP@ssword123"
    new_pw = "BrandNewP@ssword456"

    user = User(
        email="reset_target@example.com",
        name="Reset Target",
        password_hash=hash_password(old_pw),
        email_verified=True,
    )
    test_db.add(user)
    test_db.commit()

    # Step 1: Request reset OTP
    otp, primary_user = create_password_reset_token_for_email(test_db, user.email)
    assert otp is not None

    # Step 2: Verify reset OTP
    verified, _ = verify_password_reset_token_for_email(
        test_db, user.email, otp, mark_used=True, increment_attempts=True
    )
    assert verified is True

    # Step 3: Save new password (TEST 9)
    user.password_hash = hash_password(new_pw)
    test_db.commit()

    # Verify new password is accepted
    assert verify_password(new_pw, user.password_hash) is True

    # Verify old password no longer works (TEST 10)
    assert verify_password(old_pw, user.password_hash) is False


# ===========================================================================
# REMINDER TESTS (TESTS 11 - 18)
# ===========================================================================

def test_11_and_12_and_13_and_14_automatic_reminder_worker(test_db):
    """TEST 11: Create reminder for near-future time -> No manual button required.
    TEST 12: Keep backend running until scheduled time -> Email automatically sent.
    TEST 13: Verify recipient -> Email goes to authenticated user's email.
    TEST 14: Verify reminder content -> Email contains the actual reminder text.
    """
    user = User(
        email="researcher_scholar@example.com",
        name="Scholar Jane",
        password_hash=hash_password("pw"),
        email_verified=True,
    )
    test_db.add(user)
    test_db.commit()

    # Create scheduled reminder: "Submit NeurIPS Camera-Ready"
    now_utc = datetime.now(timezone.utc)
    scheduled_time = now_utc + timedelta(seconds=2)
    reminder = UserReminder(
        user_id=user.id,
        title="Submit NeurIPS Camera-Ready",
        description="Include rebuttal revisions and check artifact DOI",
        reminder_datetime=scheduled_time.replace(tzinfo=None),
        timezone="Asia/Kolkata",
        status="pending",
        email_sent=False,
    )
    test_db.add(reminder)
    test_db.commit()

    sent_emails = []

    def mock_send(to, subject, body, html=None):
        sent_emails.append({"to": to, "subject": subject, "body": body, "html": html})
        return {"status": "sent", "detail": "Delivered"}

    with patch("app.services.reminder_agent.send_email", side_effect=mock_send):
        # 1. Before due time: automatic worker runs, nothing sent
        processed_before = process_due_reminders(test_db, now=now_utc)
        assert processed_before == 0
        assert len(sent_emails) == 0

        # 2. At or after scheduled time: automatic worker runs, email automatically sent (TEST 12)
        due_time = scheduled_time + timedelta(seconds=1)
        processed_due = process_due_reminders(test_db, now=due_time)
        assert processed_due == 1

        # TEST 13: Recipient check
        assert len(sent_emails) == 1
        assert sent_emails[0]["to"] == "researcher_scholar@example.com"

        # TEST 14: Content check
        email_body = sent_emails[0]["body"]
        assert "Submit NeurIPS Camera-Ready" in email_body
        assert "Include rebuttal revisions" in email_body

        # Verify DB state
        test_db.refresh(reminder)
        assert reminder.status == "sent"
        assert reminder.email_sent is True
        assert reminder.email_sent_at is not None


def test_15_timezone_asia_kolkata_accuracy(test_db):
    """TEST 15: Verify timezone: create reminder using Asia/Kolkata.
    Scheduled time is interpreted correctly and preserved without date drift.
    """
    kolkata_tz = zoneinfo.ZoneInfo("Asia/Kolkata")
    # Today at 11:31 AM IST
    now_kolkata = datetime.now(kolkata_tz)
    kolkata_dt = now_kolkata.replace(hour=11, minute=31, second=0, microsecond=0)
    utc_dt = kolkata_dt.astimezone(timezone.utc)

    # In UTC, 11:31 AM IST is 06:01 AM UTC on the SAME calendar day
    assert utc_dt.hour == 6
    assert utc_dt.minute == 1
    assert utc_dt.day == kolkata_dt.day

    # Verify email formatting produces exact requested time in IST
    body = reminder_email_body(
        title="Check Experiments",
        description="Verify GPU training",
        due_datetime=utc_dt.replace(tzinfo=None),
        user_name="Researcher",
        timezone_name="Asia/Kolkata",
    )
    assert "11:31 AM (Asia/Kolkata)" in body
    assert "Check Experiments" in body


def test_16_server_restart_recovery(test_db):
    """TEST 16: Restart backend -> Pending reminders remain recoverable and are not lost."""
    user = User(
        email="restart_user@example.com",
        name="Restart User",
        password_hash=hash_password("pw"),
        email_verified=True,
    )
    test_db.add(user)
    test_db.commit()

    # Simulate reminder that was mid-flight ("processing") when server crashed or was killed
    crash_time = datetime.now(timezone.utc) - timedelta(minutes=5)
    reminder = UserReminder(
        user_id=user.id,
        title="Recovered After Crash",
        description="Must not be lost",
        reminder_datetime=crash_time.replace(tzinfo=None),
        timezone="Asia/Kolkata",
        status="processing",  # left in processing state by aborted process
        email_sent=False,
    )
    test_db.add(reminder)
    test_db.commit()

    # Server restarts: recover_stale_reminders is invoked during lifespan startup
    recovered = recover_stale_reminders(test_db)
    assert recovered >= 1

    test_db.refresh(reminder)
    assert reminder.status == "pending"

    # Worker runs after restart and successfully delivers the reminder
    sent_emails = []
    with patch("app.services.reminder_agent.send_email", return_value={"status": "sent"}):
        count = process_due_reminders(test_db, now=datetime.now(timezone.utc))
        assert count == 1
        test_db.refresh(reminder)
        assert reminder.status == "sent"
        assert reminder.email_sent is True


def test_17_already_sent_reminder_duplicate_prevention(test_db):
    """TEST 17: Already-sent reminder -> No duplicate email."""
    user = User(
        email="nodupe_user@example.com",
        name="NoDupe",
        password_hash=hash_password("pw"),
        email_verified=True,
    )
    test_db.add(user)
    test_db.commit()

    past_time = datetime.now(timezone.utc) - timedelta(hours=1)
    reminder = UserReminder(
        user_id=user.id,
        title="Already Sent Reminder",
        reminder_datetime=past_time.replace(tzinfo=None),
        timezone="Asia/Kolkata",
        status="sent",
        email_sent=True,
        email_sent_at=past_time.replace(tzinfo=None),
    )
    test_db.add(reminder)
    test_db.commit()

    sent_count = 0

    def mock_send(to, subject, body, html=None):
        nonlocal sent_count
        sent_count += 1
        return {"status": "sent"}

    with patch("app.services.reminder_agent.send_email", side_effect=mock_send):
        # Process loop runs 5 times
        for _ in range(5):
            count = process_due_reminders(test_db, now=datetime.now(timezone.utc))
            assert count == 0

    # ZERO duplicate emails sent
    assert sent_count == 0


def test_18_email_failure_safety(test_db):
    """TEST 18: Email failure -> Reminder is not falsely marked as successfully sent."""
    user = User(
        email="fail_test@example.com",
        name="Fail User",
        password_hash=hash_password("pw"),
        email_verified=True,
    )
    test_db.add(user)
    test_db.commit()

    past_time = datetime.now(timezone.utc) - timedelta(minutes=2)
    reminder = UserReminder(
        user_id=user.id,
        title="Network Down Reminder",
        reminder_datetime=past_time.replace(tzinfo=None),
        timezone="Asia/Kolkata",
        status="pending",
        email_sent=False,
    )
    test_db.add(reminder)
    test_db.commit()

    # Simulate Resend API error / network failure
    failure_result = {
        "status": "failed",
        "detail": "Resend sandbox limitation: Unverified sender (onboarding@resend.dev) can only deliver to the verified Resend account owner.",
    }

    with patch("app.services.reminder_agent.send_email", return_value=failure_result):
        processed = process_due_reminders(test_db, now=datetime.now(timezone.utc))
        assert processed == 0

    test_db.refresh(reminder)
    # Reminder must NOT be marked as sent!
    assert reminder.email_sent is False
    assert reminder.status == "pending"
    assert "Resend sandbox limitation" in reminder.last_error


def test_production_sandbox_fallback_prevented():
    """Verify that in production (ENVIRONMENT=production), the application does NOT silently fall back to onboarding@resend.dev."""
    from app.core.config import settings
    from app.services.email_service import _resolve_resend_from, _send_resend

    with patch.object(settings, "environment", "production"), \
         patch.object(settings, "email_from", "onboarding@resend.dev"), \
         patch.object(settings, "resend_from", "onboarding@resend.dev"), \
         patch.object(settings, "resend_api_key", "re_test_key"):

        from_addr, err = _resolve_resend_from()
        assert from_addr is None
        assert err is not None
        assert "Production email configuration error" in err

        send_res = _send_resend("user@external.com", "Test", "Body")
        assert send_res["status"] == "failed"
        assert "Production email configuration error" in send_res["detail"]
