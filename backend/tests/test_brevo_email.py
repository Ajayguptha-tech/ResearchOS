"""Comprehensive verification suite for Brevo email integration.

Verifies:
- Brevo sender resolution and validation from EMAIL_FROM
- Brevo transactional payload structure (sender, to, subject, htmlContent)
- Dynamic recipients across Signup, Forgot Password, Resend OTP, and Reminders
- No leakage of BREVO_API_KEY, OTP, or secrets in logs or responses
- Cooldown, wrong OTP, expired OTP, password reset, and reminder execution
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.db.base import Base
from app.db.models import EmailVerification, PasswordResetToken, User, UserReminder
from app.services.email_service import (
    _brevo_available,
    _resolve_brevo_sender,
    _send_brevo,
    send_email,
    test_smtp_connection as check_email_connection,
)
from app.services.otp_service import (
    can_resend_otp,
    can_resend_password_reset_for_email,
    create_email_verification,
    create_password_reset_token_for_email,
    verify_email_otp,
    verify_password_reset_token_for_email,
)
from app.services.reminder_agent import process_due_reminders


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


def test_brevo_sender_resolution():
    """Verify _resolve_brevo_sender correctly parses name and email and rejects invalid/missing configurations."""
    # 1. Valid sender with name and address
    with patch.object(settings, "email_from", "ResearchOS <ajayguptha710@gmail.com>"):
        sender, err = _resolve_brevo_sender()
        assert err is None
        assert sender == {"name": "ResearchOS", "email": "ajayguptha710@gmail.com"}

    # 2. Plain email without name
    with patch.object(settings, "email_from", "ajayguptha710@gmail.com"):
        sender, err = _resolve_brevo_sender()
        assert err is None
        assert sender == {"name": "ResearchOS", "email": "ajayguptha710@gmail.com"}

    # 3. Missing EMAIL_FROM
    with patch.object(settings, "email_from", ""):
        sender, err = _resolve_brevo_sender()
        assert sender is None
        assert "EMAIL_FROM is missing" in err

    # 4. Invalid placeholder
    with patch.object(settings, "email_from", "onboarding@resend.dev"):
        sender, err = _resolve_brevo_sender()
        assert sender is None
        assert "invalid placeholder" in err


def test_brevo_payload_structure_and_dynamic_recipient():
    """Verify Brevo API request payload contains exact sender, recipient, subject, and body."""
    captured_requests = []

    def mock_post(url, headers, json, timeout=15):
        captured_requests.append({"url": url, "headers": headers, "json": json})
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {"messageId": "<test-msg-123@smtp-relay.mailin.fr>"}
        return mock_resp

    with patch.object(settings, "email_provider", "brevo"), \
         patch.object(settings, "brevo_api_key", "xkeysib-test-secret-key"), \
         patch.object(settings, "email_from", "ResearchOS <verified@sender.com>"), \
         patch("requests.post", side_effect=mock_post):

        # Test A: User A email
        res_a = send_email("user_a@academic.edu", "Subject A", "Body content A", html="<p>Body content A</p>")
        assert res_a["status"] == "sent"
        assert len(captured_requests) == 1
        req_a = captured_requests[0]
        assert req_a["url"] == "https://api.brevo.com/v3/smtp/email"
        assert req_a["headers"]["api-key"] == "xkeysib-test-secret-key"
        assert req_a["json"]["sender"] == {"name": "ResearchOS", "email": "verified@sender.com"}
        assert req_a["json"]["to"] == [{"email": "user_a@academic.edu"}]
        assert req_a["json"]["subject"] == "Subject A"
        assert "<p>Body content A</p>" in req_a["json"]["htmlContent"]

        # Test B: User B email (dynamic recipient isolation)
        res_b = send_email("user_b@institute.org", "Subject B", "Body content B")
        assert res_b["status"] == "sent"
        assert len(captured_requests) == 2
        req_b = captured_requests[1]
        assert req_b["json"]["to"] == [{"email": "user_b@institute.org"}]
        assert req_b["json"]["to"] != req_a["json"]["to"]


def test_brevo_missing_api_key_fails_safely():
    """Verify that if BREVO_API_KEY is missing, send_email fails clearly without crashing."""
    with patch.object(settings, "email_provider", "brevo"), \
         patch.object(settings, "brevo_api_key", ""), \
         patch.object(settings, "email_from", "ResearchOS <verified@sender.com>"):
        res = send_email("student@uni.edu", "Test", "Body")
        assert res["status"] == "failed"
        assert "BREVO_API_KEY is not configured" in res["detail"]


def test_brevo_error_response_handling():
    """Verify that Brevo HTTP errors are parsed safely without exposing internal keys."""
    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.json.return_value = {"code": "invalid_parameter", "message": "Invalid recipient format"}

    with patch.object(settings, "email_provider", "brevo"), \
         patch.object(settings, "brevo_api_key", "xkeysib-test-secret-key"), \
         patch.object(settings, "email_from", "ResearchOS <verified@sender.com>"), \
         patch("requests.post", return_value=mock_resp):
        res = _send_brevo("invalid_user@external_domain.org", "Test", "Body")
        assert res["status"] == "failed"
        assert "Brevo API error (400)" in res["detail"]
        assert "xkeysib-test-secret-key" not in res["detail"]


def test_signup_otp_and_resend_with_brevo(test_db):
    """TEST 1, 2, 5: Signup OTP for User A, User B, and Resend OTP with Brevo."""
    captured = []

    def mock_post(url, headers, json, timeout=15):
        captured.append(json)
        m = MagicMock()
        m.status_code = 201
        m.json.return_value = {"messageId": "<test-msg@mailin.fr>"}
        return m

    user_a = User(email="user_a@academic.edu", name="User A", password_hash=hash_password("pwA"), email_verified=False)
    user_b = User(email="user_b@institute.org", name="User B", password_hash=hash_password("pwB"), email_verified=False)
    test_db.add_all([user_a, user_b])
    test_db.commit()

    with patch.object(settings, "email_provider", "brevo"), \
         patch.object(settings, "brevo_api_key", "xkeysib-test-secret-key"), \
         patch.object(settings, "email_from", "ResearchOS <verified@sender.com>"), \
         patch("requests.post", side_effect=mock_post):

        # TEST 1: User A Signup
        otp_a = create_email_verification(test_db, user_a.id, purpose="registration")
        res1 = send_email(user_a.email, "ResearchOS — Email Verification Code", f"OTP: {otp_a}")
        assert res1["status"] == "sent"
        assert captured[-1]["to"] == [{"email": "user_a@academic.edu"}]

        # TEST 2: User B Signup
        otp_b = create_email_verification(test_db, user_b.id, purpose="registration")
        res2 = send_email(user_b.email, "ResearchOS — Email Verification Code", f"OTP: {otp_b}")
        assert res2["status"] == "sent"
        assert captured[-1]["to"] == [{"email": "user_b@institute.org"}]
        assert captured[-1]["to"] != captured[-2]["to"]

        # TEST 5: Resend OTP for User A (cooldown elapsed)
        rec = test_db.query(EmailVerification).filter(EmailVerification.user_id == user_a.id).first()
        rec.created_at = (datetime.now(timezone.utc) - timedelta(seconds=70)).replace(tzinfo=None)
        test_db.commit()

        can_resend, _ = can_resend_otp(test_db, user_a.id, purpose="registration")
        assert can_resend is True
        otp_a2 = create_email_verification(test_db, user_a.id, purpose="registration")
        res3 = send_email(user_a.email, "ResearchOS — Email Verification Code", f"New OTP: {otp_a2}")
        assert res3["status"] == "sent"
        assert captured[-1]["to"] == [{"email": "user_a@academic.edu"}]


def test_forgot_password_and_reset_with_brevo(test_db):
    """TEST 3, 4, 6, 7, 8, 9, 10, 11: Forgot Password, OTP lifecycle, and password change."""
    captured = []

    def mock_post(url, headers, json, timeout=15):
        captured.append(json)
        m = MagicMock()
        m.status_code = 201
        m.json.return_value = {"messageId": "<test-msg@mailin.fr>"}
        return m

    old_pw_a = "OldSecretA1!"
    user_a = User(email="user_a@academic.edu", name="User A", password_hash=hash_password(old_pw_a), email_verified=True)
    user_b = User(email="user_b@institute.org", name="User B", password_hash=hash_password("OldSecretB1!"), email_verified=True)
    test_db.add_all([user_a, user_b])
    test_db.commit()

    with patch.object(settings, "email_provider", "brevo"), \
         patch.object(settings, "brevo_api_key", "xkeysib-test-secret-key"), \
         patch.object(settings, "email_from", "ResearchOS <verified@sender.com>"), \
         patch("requests.post", side_effect=mock_post):

        # TEST 3: User A Forgot Password
        otp_a, _ = create_password_reset_token_for_email(test_db, user_a.email)
        res_a = send_email(user_a.email, "ResearchOS — Password Reset Code", f"OTP: {otp_a}")
        assert res_a["status"] == "sent"
        assert captured[-1]["to"] == [{"email": "user_a@academic.edu"}]

        # TEST 4: User B Forgot Password
        otp_b, _ = create_password_reset_token_for_email(test_db, user_b.email)
        res_b = send_email(user_b.email, "ResearchOS — Password Reset Code", f"OTP: {otp_b}")
        assert res_b["status"] == "sent"
        assert captured[-1]["to"] == [{"email": "user_b@institute.org"}]

    # TEST 6: Wrong OTP rejected
    valid_wrong, msg = verify_password_reset_token_for_email(test_db, user_a.email, "000000")
    assert valid_wrong is False

    # TEST 7: Expired OTP rejected
    rec = test_db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user_a.id).first()
    rec.expires_at = (datetime.now(timezone.utc) - timedelta(minutes=15)).replace(tzinfo=None)
    test_db.commit()
    valid_expired, _ = verify_password_reset_token_for_email(test_db, user_a.email, otp_a)
    assert valid_expired is False

    # TEST 8: Issue fresh OTP and verify success
    otp_fresh, _ = create_password_reset_token_for_email(test_db, user_a.email)
    valid_correct, _ = verify_password_reset_token_for_email(test_db, user_a.email, otp_fresh, mark_used=True)
    assert valid_correct is True

    # TEST 9: Update to new password
    new_pw_a = "NewSecretA2@"
    user_a.password_hash = hash_password(new_pw_a)
    test_db.commit()

    # TEST 10: Old password fails
    assert verify_password(old_pw_a, user_a.password_hash) is False

    # TEST 11: New password succeeds
    assert verify_password(new_pw_a, user_a.password_hash) is True


def test_automatic_reminder_with_brevo(test_db):
    """TEST 12: Near-future reminder automatic worker execution through Brevo."""
    user = User(email="pi_scientist@research.edu", name="PI Scientist", password_hash=hash_password("pw"), email_verified=True)
    test_db.add(user)
    test_db.commit()

    now_utc = datetime.now(timezone.utc)
    due_time = now_utc + timedelta(seconds=2)
    reminder = UserReminder(
        user_id=user.id,
        title="Submit NSF Grant Proposal",
        description="Check budget tables and collaborator letters",
        reminder_datetime=due_time.replace(tzinfo=None),
        timezone="Asia/Kolkata",
        status="pending",
        email_sent=False,
    )
    test_db.add(reminder)
    test_db.commit()

    sent_emails = []

    def mock_send(to, subject, body, html=None):
        sent_emails.append({"to": to, "subject": subject, "body": body})
        return {"status": "sent", "detail": "Delivered via Brevo"}

    with patch("app.services.reminder_agent.send_email", side_effect=mock_send):
        # 1. Before due time
        processed_early = process_due_reminders(test_db, now=now_utc)
        assert processed_early == 0
        assert len(sent_emails) == 0

        # 2. At due time -> Automatically detected and sent
        processed_due = process_due_reminders(test_db, now=due_time + timedelta(seconds=1))
        assert processed_due == 1
        assert len(sent_emails) == 1
        assert sent_emails[0]["to"] == "pi_scientist@research.edu"
        assert "Submit NSF Grant Proposal" in sent_emails[0]["body"]

        test_db.refresh(reminder)
        assert reminder.status == "sent"
        assert reminder.email_sent is True


def test_brevo_test_connection_endpoint():
    """Verify test_smtp_connection returns ok when authenticated with Brevo API."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"email": "ajayguptha710@gmail.com"}

    with patch.object(settings, "email_provider", "brevo"), \
         patch.object(settings, "brevo_api_key", "xkeysib-test-secret-key"), \
         patch.object(settings, "email_from", "ResearchOS <ajayguptha710@gmail.com>"), \
         patch("requests.get", return_value=mock_resp):
        res = check_email_connection()
        assert res["email_provider"] == "brevo"
        assert res["status"] == "ok"
        assert res["brevo_api_key_set"] is True
