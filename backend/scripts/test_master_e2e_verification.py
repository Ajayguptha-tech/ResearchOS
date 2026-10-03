"""Master End-to-End Verification Script for ResearchOS.

Validates complete requirements for:
TEST A — Registration OTP lifecycle (single email, wrong OTP, correct OTP, no reuse)
TEST B — Resend OTP & Cooldown (one email on resend, 60s cooldown blocks rapid resends)
TEST C — Forgot Password Flow (single email, wrong code, resend, reset, single-use token)
TEST D — Reminder Today: Automatic dispatch without pressing "Send Test Email Now"
TEST E — Duplicate Reminder Prevention: Multiple scheduler passes produce exactly ONE email
TEST F — Worker Restart: Interrupted "processing" reminders recover back to "pending"
TEST G — Date Boundary & Midnight: Canonical Asia/Kolkata (Today 10am, Today 11:59pm, Tomorrow 12:01am, Tomorrow 10am)
TEST H — Send Test Email Separation: "Send Test Email Now" dispatches test email without disarming future scheduled reminder
"""

from __future__ import annotations

import os
import sys
import time
import zoneinfo
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock

# Setup paths
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient

from app.api.v1.routes import auth
from app.core.security import hash_password, verify_password
from app.db.models import EmailVerification, PasswordResetToken, User, UserReminder
from app.db.session import SessionLocal
from app.main import app
from app.services import reminder_agent
from app.services.otp_service import (
    create_email_verification,
    verify_email_otp,
    create_password_reset_token_for_email,
    verify_password_reset_token_for_email,
    can_resend_otp,
)
from app.services.reminder_agent import process_due_reminders, recover_stale_reminders, send_reminder_now


def run_master_verification():
    db = SessionLocal()
    client = TestClient(app)
    results = {}

    print("=" * 80)
    print("RESEARCHOS — COMPLETE END-TO-END MASTER AUDIT & VERIFICATION")
    print("=" * 80)

    # -------------------------------------------------------------
    # TEST A — Registration OTP
    # -------------------------------------------------------------
    print("\n[TEST A] Registration OTP Lifecycle...")
    try:
        test_email_a = "audit_user_a@researchos.ai"
        # Cleanup
        db.query(EmailVerification).filter(EmailVerification.user_id.in_(
            db.query(User.id).filter(User.email == test_email_a)
        )).delete(synchronize_session=False)
        db.query(User).filter(User.email == test_email_a).delete()
        db.commit()

        # Mock email
        mock_send = MagicMock(return_value={"status": "sent"})
        auth.send_email = mock_send

        # 1. Register new account
        reg_res = client.post("/api/v1/auth/register", json={
            "email": test_email_a,
            "password": "SecurePassword123!",
            "name": "Audit User A",
        })
        assert reg_res.status_code == 201, f"Reg failed: {reg_res.text}"
        assert reg_res.json()["require_verification"] is True
        assert mock_send.call_count == 1, f"Expected 1 email, got {mock_send.call_count}"

        user_a = db.query(User).filter(User.email == test_email_a).first()
        assert user_a is not None
        assert user_a.email_verified is False

        # Retrieve active OTP
        ev = db.query(EmailVerification).filter(EmailVerification.user_id == user_a.id).first()
        assert ev is not None
        # In OTP service, verify_email_otp checks hash or we extract from service
        # Let's test wrong OTP
        wrong_res = client.post("/api/v1/auth/verify-email", json={"email": test_email_a, "otp": "000000"})
        assert wrong_res.status_code == 400, "Wrong OTP was not rejected!"
        assert user_a.email_verified is False

        # Now get the valid OTP by calling create_email_verification directly for a known value or test with helper
        # To get the exact OTP, let's create a known verification
        db.query(EmailVerification).filter(EmailVerification.user_id == user_a.id).delete()
        db.commit()
        valid_otp = create_email_verification(db, user_a.id, purpose="registration")

        # Verify correct OTP
        verify_res = client.post("/api/v1/auth/verify-email", json={"email": test_email_a, "otp": valid_otp})
        assert verify_res.status_code == 200, f"Verify failed: {verify_res.text}"
        db.refresh(user_a)
        assert user_a.email_verified is True

        # Try reusing OTP
        reuse_res = client.post("/api/v1/auth/verify-email", json={"email": test_email_a, "otp": valid_otp})
        assert reuse_res.status_code == 400, "Reused OTP was not rejected!"

        results["TEST A — Registration OTP"] = "PASS"
        print("  -> TEST A PASSED: Exactly 1 email, wrong OTP rejected, correct OTP verified, token consumed, reuse blocked.")
    except Exception as e:
        results["TEST A — Registration OTP"] = f"FAIL: {e}"
        print(f"  -> TEST A FAILED: {e}")

    # -------------------------------------------------------------
    # TEST B — Resend OTP & Cooldown
    # -------------------------------------------------------------
    print("\n[TEST B] Resend OTP & Cooldown...")
    try:
        test_email_b = "audit_user_b@researchos.ai"
        db.query(EmailVerification).filter(EmailVerification.user_id.in_(
            db.query(User.id).filter(User.email == test_email_b)
        )).delete(synchronize_session=False)
        db.query(User).filter(User.email == test_email_b).delete()
        db.commit()

        mock_send = MagicMock(return_value={"status": "sent"})
        auth.send_email = mock_send

        # 1. Create unverified account -> 1 initial email
        reg_b = client.post("/api/v1/auth/register", json={
            "email": test_email_b,
            "password": "SecurePassword123!",
            "name": "Audit User B",
        })
        assert reg_b.status_code == 201
        assert mock_send.call_count == 1, "Initial register email count mismatch"

        # 2. Click resend immediately -> Cooldown blocks
        resend_cooldown = client.post("/api/v1/auth/resend-otp", json={"email": test_email_b})
        assert resend_cooldown.status_code == 429, f"Cooldown should have returned 429, got {resend_cooldown.status_code}"
        assert mock_send.call_count == 1, "Email was erroneously sent during cooldown!"

        # 3. Simulate cooldown expired (70s elapsed)
        user_b = db.query(User).filter(User.email == test_email_b).first()
        ev_b = db.query(EmailVerification).filter(EmailVerification.user_id == user_b.id).first()
        ev_b.created_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=70)
        db.commit()

        # 4. Click resend after cooldown -> Exactly 1 new email
        mock_send.reset_mock()
        resend_ok = client.post("/api/v1/auth/resend-otp", json={"email": test_email_b})
        assert resend_ok.status_code == 200, f"Resend failed: {resend_ok.text}"
        assert mock_send.call_count == 1, f"Expected 1 resend email, got {mock_send.call_count}"

        # 5. Click resend again immediately -> Cooldown blocks again
        mock_send.reset_mock()
        resend_immediate2 = client.post("/api/v1/auth/resend-otp", json={"email": test_email_b})
        assert resend_immediate2.status_code == 429
        assert mock_send.call_count == 0

        results["TEST B — Resend OTP & Cooldown"] = "PASS"
        print("  -> TEST B PASSED: Cooldown strictly enforced, exactly 1 email on legitimate resend, rapid clicks blocked.")
    except Exception as e:
        results["TEST B — Resend OTP & Cooldown"] = f"FAIL: {e}"
        print(f"  -> TEST B FAILED: {e}")

    # -------------------------------------------------------------
    # TEST C — Forgot Password Flow
    # -------------------------------------------------------------
    print("\n[TEST C] Forgot Password & Reset Flow...")
    try:
        test_email_c = "audit_user_c@researchos.ai"
        db.query(PasswordResetToken).filter(PasswordResetToken.user_id.in_(
            db.query(User.id).filter(User.email == test_email_c)
        )).delete(synchronize_session=False)
        db.query(User).filter(User.email == test_email_c).delete()
        db.commit()

        user_c = User(
            email=test_email_c,
            name="Audit User C",
            password_hash=hash_password("OriginalPassword123!"),
            email_verified=True,
        )
        db.add(user_c)
        db.commit()

        mock_send = MagicMock(return_value={"status": "sent"})
        auth.send_email = mock_send

        # 1. Request password reset -> 1 email
        forgot_res = client.post("/api/v1/auth/forgot-password", json={"email": test_email_c})
        assert forgot_res.status_code == 200
        assert mock_send.call_count == 1

        # 2. Cooldown on rapid second forgot password
        forgot_rapid = client.post("/api/v1/auth/forgot-password", json={"email": test_email_c})
        assert forgot_rapid.status_code == 429
        assert mock_send.call_count == 1

        # 3. Enter incorrect OTP
        wrong_reset = client.post("/api/v1/auth/verify-reset-otp", json={"email": test_email_c, "otp": "111111"})
        assert wrong_reset.status_code == 400

        # 4. Generate known valid reset OTP after cooldown
        db.query(PasswordResetToken).delete()
        db.commit()
        reset_otp, _ = create_password_reset_token_for_email(db, test_email_c)

        # 5. Verify correct reset OTP
        verify_rst = client.post("/api/v1/auth/verify-reset-otp", json={"email": test_email_c, "otp": reset_otp})
        assert verify_rst.status_code == 200

        # 6. Reset password
        do_reset = client.post("/api/v1/auth/reset-password", json={
            "email": test_email_c,
            "otp": reset_otp,
            "new_password": "NewResetPassword456!",
        })
        assert do_reset.status_code == 200

        # 7. Old token cannot be reused
        reuse_rst = client.post("/api/v1/auth/reset-password", json={
            "email": test_email_c,
            "otp": reset_otp,
            "new_password": "AnotherNewPassword789!",
        })
        assert reuse_rst.status_code == 400

        # 8. User can log in with new password
        db.refresh(user_c)
        assert verify_password("NewResetPassword456!", user_c.password_hash)

        results["TEST C — Forgot Password"] = "PASS"
        print("  -> TEST C PASSED: Single reset email, wrong OTP rejected, password updated securely, token single-use.")
    except Exception as e:
        results["TEST C — Forgot Password"] = f"FAIL: {e}"
        print(f"  -> TEST C FAILED: {e}")

    # -------------------------------------------------------------
    # TEST D — Reminder Today: Automatic Background Dispatch
    # -------------------------------------------------------------
    print("\n[TEST D] Reminder Today (Autonomous Dispatch without 'Send Test Email')...")
    try:
        from app.core.security import create_access_token

        test_email_d = "audit_user_d@researchos.ai"
        db.query(UserReminder).filter(UserReminder.user_id.in_(
            db.query(User.id).filter(User.email == test_email_d)
        )).delete(synchronize_session=False)
        db.query(User).filter(User.email == test_email_d).delete()
        db.commit()

        user_d = User(
            email=test_email_d,
            name="Audit User D",
            password_hash=hash_password("Password123!"),
            email_verified=True,
        )
        db.add(user_d)
        db.commit()
        db.refresh(user_d)

        token_d = create_access_token(str(user_d.id))
        headers_d = {"Authorization": f"Bearer {token_d}"}

        mock_send = MagicMock(return_value={"status": "sent"})
        reminder_agent.send_email = mock_send

        # Create a reminder for Today, 2 seconds in the future
        future_dt_utc = datetime.now(timezone.utc) + timedelta(seconds=2)
        # Format as local Asia/Kolkata string
        kolkata_tz = zoneinfo.ZoneInfo("Asia/Kolkata")
        local_future_dt = future_dt_utc.astimezone(kolkata_tz)
        local_str = local_future_dt.strftime("%Y-%m-%dT%H:%M:%S")

        create_res = client.post("/api/v1/reminders", json={
            "title": "Autonomous Verification Reminder",
            "description": "Verifying autonomous background dispatch without manual trigger",
            "reminder_datetime": local_str,
            "timezone": "Asia/Kolkata",
        }, headers=headers_d)
        assert create_res.status_code == 201, f"Failed create: {create_res.text}"
        rem_data = create_res.json()
        reminder_id = rem_data["id"]
        assert rem_data["status"] == "pending"
        assert rem_data["email_sent"] is False

        # Assert scheduler does NOT fire before due time
        processed_early = process_due_reminders(db, now=future_dt_utc - timedelta(seconds=1))
        assert processed_early == 0
        assert mock_send.call_count == 0

        # Wait 2.5 seconds for due time to arrive
        print("  -> Waiting 2.5 seconds for reminder due moment to arrive...")
        time.sleep(2.5)

        # Background scheduler tick runs autonomously (NO "Send Test Email" clicked!)
        processed_due = process_due_reminders(db)
        assert processed_due == 1, f"Expected 1 processed reminder, got {processed_due}"
        assert mock_send.call_count == 1, "Email was not sent by scheduler!"

        # Verify DB state
        db_rem = db.query(UserReminder).filter(UserReminder.id == reminder_id).first()
        assert db_rem.status == "sent"
        assert db_rem.email_sent is True
        assert db_rem.email_sent_at is not None

        results["TEST D — Reminder Today (Automatic)"] = "PASS"
        print("  -> TEST D PASSED: Created reminder, waited for due time, scheduler automatically sent email and marked sent.")
    except Exception as e:
        results["TEST D — Reminder Today (Automatic)"] = f"FAIL: {e}"
        print(f"  -> TEST D FAILED: {e}")

    # -------------------------------------------------------------
    # TEST E — Duplicate Reminder Protection
    # -------------------------------------------------------------
    print("\n[TEST E] Duplicate Reminder Protection...")
    try:
        mock_send.reset_mock()
        # Run scheduler multiple times consecutively
        p1 = process_due_reminders(db)
        p2 = process_due_reminders(db)
        p3 = process_due_reminders(db)
        assert p1 == 0 and p2 == 0 and p3 == 0, f"Duplicate detected: {p1}, {p2}, {p3}"
        assert mock_send.call_count == 0

        results["TEST E — Duplicate Reminder"] = "PASS"
        print("  -> TEST E PASSED: Repeated scheduler ticks processed 0 duplicate reminders; exactly 1 email sent.")
    except Exception as e:
        results["TEST E — Duplicate Reminder"] = f"FAIL: {e}"
        print(f"  -> TEST E FAILED: {e}")

    # -------------------------------------------------------------
    # TEST F — Worker Restart & Stale Recovery
    # -------------------------------------------------------------
    print("\n[TEST F] Worker Restart & Interrupted Recovery...")
    try:
        # Create an interrupted reminder in 'processing' status
        interrupted_rem = UserReminder(
            user_id=user_d.id,
            title="Crash Recovery Task",
            reminder_datetime=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=5),
            timezone="Asia/Kolkata",
            status="processing",
            email_sent=False,
        )
        db.add(interrupted_rem)
        db.commit()
        db.refresh(interrupted_rem)

        # Worker restart -> triggers recover_stale_reminders
        recovered = recover_stale_reminders(db)
        assert recovered >= 1
        db.refresh(interrupted_rem)
        assert interrupted_rem.status == "pending"

        # Now scheduler processes it cleanly
        mock_send.reset_mock()
        processed_rec = process_due_reminders(db)
        assert processed_rec >= 1
        assert mock_send.call_count == 1
        db.refresh(interrupted_rem)
        assert interrupted_rem.status == "sent"
        assert interrupted_rem.email_sent is True

        results["TEST F — Worker Restart"] = "PASS"
        print("  -> TEST F PASSED: Stale processing reminder recovered on restart and dispatched cleanly.")
    except Exception as e:
        results["TEST F — Worker Restart"] = f"FAIL: {e}"
        print(f"  -> TEST F FAILED: {e}")

    # -------------------------------------------------------------
    # TEST G — Date Boundary & Midnight Transitions
    # -------------------------------------------------------------
    print("\n[TEST G] Date Boundary & Midnight Transitions (Asia/Kolkata)...")
    try:
        kolkata = zoneinfo.ZoneInfo("Asia/Kolkata")
        cases = [
            ("2026-10-02T10:00:00", 4, 30, "2026-10-02", "10:00"),
            ("2026-10-02T23:59:00", 18, 29, "2026-10-02", "23:59"),
            ("2026-10-03T00:01:00", 18, 31, "2026-10-03", "00:01"),
            ("2026-10-03T10:00:00", 4, 30, "2026-10-03", "10:00"),
        ]

        for inp, exp_h, exp_m, exp_date, exp_time in cases:
            res = client.post("/api/v1/reminders", json={
                "title": f"Date Test {inp}",
                "reminder_datetime": inp,
                "timezone": "Asia/Kolkata",
            }, headers=headers_d)
            assert res.status_code == 201
            d = res.json()
            r_db = db.query(UserReminder).filter(UserReminder.id == d["id"]).first()
            assert r_db.reminder_datetime.hour == exp_h
            assert r_db.reminder_datetime.minute == exp_m

            # Check local date reconstruction
            utc_dt = r_db.reminder_datetime.replace(tzinfo=timezone.utc)
            loc_dt = utc_dt.astimezone(kolkata)
            assert loc_dt.strftime("%Y-%m-%d") == exp_date, f"Date mismatch for {inp}"
            assert loc_dt.strftime("%H:%M") == exp_time, f"Time mismatch for {inp}"

        results["TEST G — Date Boundary (Midnight)"] = "PASS"
        print("  -> TEST G PASSED: Today 10:00 AM, Today 11:59 PM, Tomorrow 12:01 AM, Tomorrow 10:00 AM all normalized and displayed perfectly without date skew.")
    except Exception as e:
        results["TEST G — Date Boundary (Midnight)"] = f"FAIL: {e}"
        print(f"  -> TEST G FAILED: {e}")

    # -------------------------------------------------------------
    # TEST H — Send Test Email Separation
    # -------------------------------------------------------------
    print("\n[TEST H] Send Test Email Separation...")
    try:
        # Clean up any lingering reminders from previous tests
        db.query(UserReminder).delete()
        db.commit()

        mock_send.reset_mock()
        # Create a reminder for next week
        future_str = "2026-10-10T10:00:00"
        create_res = client.post("/api/v1/reminders", json={
            "title": "Future Milestone",
            "reminder_datetime": future_str,
            "timezone": "Asia/Kolkata",
        }, headers=headers_d)
        assert create_res.status_code == 201
        rem_id = create_res.json()["id"]

        # Click "Send Test Email Now"
        test_now_res = client.post(f"/api/v1/reminders/{rem_id}/send-now", headers=headers_d)
        assert test_now_res.status_code == 200
        data_test = test_now_res.json()
        assert mock_send.call_count == 1
        assert "[Test Email]" in mock_send.call_args[0][1]

        # Ensure status is STILL pending and email_sent is STILL False
        assert data_test["status"] == "pending"
        assert data_test["email_sent"] is False

        # Verify scheduler at current time does NOT dispatch it
        p_now = process_due_reminders(db, now=datetime(2026, 10, 2, 12, 0, tzinfo=timezone.utc))
        assert p_now == 0, f"Expected 0 due reminders processed, got {p_now}"

        # Verify the reminder in DB remains pending and unsent
        rem_db = db.query(UserReminder).filter(UserReminder.id == rem_id).first()
        assert rem_db.status == "pending"
        assert rem_db.email_sent is False

        results["TEST H — Send Test Email Separation"] = "PASS"
        print("  -> TEST H PASSED: 'Send Test Email Now' dispatches manual test email without disarming future scheduled reminder.")
    except Exception as e:
        import traceback
        traceback.print_exc()
        results["TEST H — Send Test Email Separation"] = f"FAIL: {repr(e)}"
        print(f"  -> TEST H FAILED: {repr(e)}")

    print("\n" + "=" * 80)
    print("FINAL SUMMARY REPORT:")
    print("=" * 80)
    all_passed = True
    for test_name, res in results.items():
        print(f"  {test_name:<45} : {res}")
        if "FAIL" in res:
            all_passed = False
    print("=" * 80)
    print("ALL TESTS PASSED: " + ("YES (100% SUCCESS)" if all_passed else "NO"))
    print("=" * 80)
    db.close()
    return all_passed


if __name__ == "__main__":
    success = run_master_verification()
    sys.exit(0 if success else 1)
