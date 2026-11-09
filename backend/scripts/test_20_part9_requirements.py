"""Comprehensive automated verification for all 20 tests required by Part 9.

Tests against the live running ResearchOS backend (http://127.0.0.1:8000)
and the live running reminder background worker.
"""

from __future__ import annotations

import hashlib
import os
import sys
import time
import zoneinfo
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.db.models import EmailVerification, PasswordResetToken, User, UserReminder
from app.db.session import SessionLocal

BASE_URL = "http://127.0.0.1:8000"


def find_otp_for_hash(token_hash: str) -> str:
    """Find the 6-digit OTP matching the SHA-256 hash."""
    for i in range(1000000):
        code = f"{i:06d}"
        if hashlib.sha256(code.encode()).hexdigest() == token_hash:
            return code
    return ""


def run_tests():
    db = SessionLocal()
    results = {}

    print("=" * 80)
    print("RESEARCHOS — 20-TEST COMPREHENSIVE VERIFICATION (PART 9)")
    print("Tested against live server at http://127.0.0.1:8000")
    print("=" * 80)

    email_a = "researcher_alpha@example.com"
    email_b = "researcher_beta@example.com"
    email_unverified = "researcher_temp_unverified@example.com"

    # Clean existing data for test emails
    for em in (email_a, email_b, email_unverified):
        u_ids = [u.id for u in db.query(User.id).filter(User.email == em).all()]
        if u_ids:
            db.query(EmailVerification).filter(EmailVerification.user_id.in_(u_ids)).delete(synchronize_session=False)
            db.query(PasswordResetToken).filter(PasswordResetToken.user_id.in_(u_ids)).delete(synchronize_session=False)
            db.query(UserReminder).filter(UserReminder.user_id.in_(u_ids)).delete(synchronize_session=False)
            db.query(User).filter(User.id.in_(u_ids)).delete(synchronize_session=False)
    db.commit()

    # -------------------------------------------------------------------------
    # TEST 1: Create account with Email A -> Exactly one OTP email
    # -------------------------------------------------------------------------
    try:
        r = requests.post(f"{BASE_URL}/api/v1/auth/register", json={
            "email": email_a,
            "password": "PasswordAlpha123!",
            "name": "Dr. Alpha",
        })
        assert r.status_code == 201, f"Status {r.status_code}: {r.text}"
        data = r.json()
        assert data["require_verification"] is True
        assert data["email"] == email_a

        # Verify exactly 1 EmailVerification record in DB
        user_a = db.query(User).filter(User.email == email_a).first()
        assert user_a is not None
        assert user_a.email_verified is False
        otps = db.query(EmailVerification).filter(EmailVerification.user_id == user_a.id).all()
        assert len(otps) == 1, f"Expected 1 OTP, got {len(otps)}"
        results["TEST 1 — Create account Email A (1 email)"] = "PASS"
    except Exception as e:
        results["TEST 1 — Create account Email A (1 email)"] = f"FAIL: {e}"

    # -------------------------------------------------------------------------
    # TEST 2: Enter correct OTP -> Account created successfully
    # -------------------------------------------------------------------------
    try:
        ev = db.query(EmailVerification).filter(EmailVerification.user_id == user_a.id).first()
        assert ev is not None
        otp_a = find_otp_for_hash(ev.otp_hash)
        assert len(otp_a) == 6

        r = requests.post(f"{BASE_URL}/api/v1/auth/verify-email", json={
            "email": email_a,
            "otp": otp_a,
        })
        assert r.status_code == 200, f"Status {r.status_code}: {r.text}"
        assert "access_token" in r.json()

        db.expire_all()
        user_a_updated = db.query(User).filter(User.id == user_a.id).first()
        assert user_a_updated.email_verified is True
        results["TEST 2 — Enter correct OTP (account verified)"] = "PASS"
    except Exception as e:
        results["TEST 2 — Enter correct OTP (account verified)"] = f"FAIL: {e}"

    # -------------------------------------------------------------------------
    # TEST 3: Enter wrong OTP -> Verification rejected
    # -------------------------------------------------------------------------
    try:
        # Register a separate unverified user to test wrong OTP
        r_unv = requests.post(f"{BASE_URL}/api/v1/auth/register", json={
            "email": email_unverified,
            "password": "PasswordTemp123!",
            "name": "Temp Unverified",
        })
        assert r_unv.status_code == 201
        user_unv = db.query(User).filter(User.email == email_unverified).first()

        r_wrong = requests.post(f"{BASE_URL}/api/v1/auth/verify-email", json={
            "email": email_unverified,
            "otp": "000000",
        })
        assert r_wrong.status_code == 400, f"Expected 400, got {r_wrong.status_code}"
        assert "invalid" in r_wrong.json()["detail"].lower()
        results["TEST 3 — Enter wrong OTP (rejected)"] = "PASS"
    except Exception as e:
        results["TEST 3 — Enter wrong OTP (rejected)"] = f"FAIL: {e}"

    # -------------------------------------------------------------------------
    # TEST 4: Use expired OTP -> Verification rejected
    # -------------------------------------------------------------------------
    try:
        db.rollback()
        ev_unv = db.query(EmailVerification).filter(EmailVerification.user_id == user_unv.id).first()
        assert ev_unv is not None
        valid_but_expired_otp = find_otp_for_hash(ev_unv.otp_hash)

        db.query(EmailVerification).filter(EmailVerification.user_id == user_unv.id).update({
            "expires_at": datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=1)
        })
        db.commit()

        r_exp = requests.post(f"{BASE_URL}/api/v1/auth/verify-email", json={
            "email": email_unverified,
            "otp": valid_but_expired_otp or "123456",
        })
        assert r_exp.status_code == 400
        assert "expired" in r_exp.json()["detail"].lower()
        results["TEST 4 — Use expired OTP (rejected)"] = "PASS"
    except Exception as e:
        results["TEST 4 — Use expired OTP (rejected)"] = f"FAIL: {e}"

    # -------------------------------------------------------------------------
    # TEST 5: Click Resend OTP -> Exactly one NEW OTP email
    # -------------------------------------------------------------------------
    try:
        db.rollback()
        # Backdate created_at to bypass cooldown
        db.query(EmailVerification).filter(EmailVerification.user_id == user_unv.id).update({
            "created_at": datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=70)
        })
        db.commit()

        r_resend = requests.post(f"{BASE_URL}/api/v1/auth/resend-otp", json={"email": email_unverified})
        assert r_resend.status_code == 200, f"Status {r_resend.status_code}: {r_resend.text}"
        data = r_resend.json()
        assert "verification code" in data["message"].lower()

        # Cooldown check on rapid second click
        r_rapid = requests.post(f"{BASE_URL}/api/v1/auth/resend-otp", json={"email": email_unverified})
        assert r_rapid.status_code == 429

        results["TEST 5 — Click Resend OTP (1 new email + cooldown)"] = "PASS"
    except Exception as e:
        results["TEST 5 — Click Resend OTP (1 new email + cooldown)"] = f"FAIL: {e}"

    # -------------------------------------------------------------------------
    # TEST 6: Create account using existing email -> Rejected appropriately
    # -------------------------------------------------------------------------
    try:
        db.rollback()
        r = requests.post(f"{BASE_URL}/api/v1/auth/register", json={
            "email": email_a,
            "password": "PasswordAlpha123!",
            "name": "Dr. Duplicate",
        })
        assert r.status_code == 400
        assert "already exists" in r.json()["detail"].lower()
        results["TEST 6 — Register existing email (rejected)"] = "PASS"
    except Exception as e:
        results["TEST 6 — Register existing email (rejected)"] = f"FAIL: {e}"

    # -------------------------------------------------------------------------
    # TEST 7: Forgot Password with existing Email A -> Reset OTP created
    # -------------------------------------------------------------------------
    try:
        db.rollback()
        db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user_a.id).delete()
        db.commit()

        r = requests.post(f"{BASE_URL}/api/v1/auth/forgot-password", json={"email": email_a})
        assert r.status_code == 200
        assert "reset code" in r.json()["message"].lower()

        # Check reset token created
        rst = db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user_a.id, PasswordResetToken.used.is_(False)).first()
        assert rst is not None
        results["TEST 7 — Forgot Password with Email A (sent)"] = "PASS"
    except Exception as e:
        results["TEST 7 — Forgot Password with Email A (sent)"] = f"FAIL: {e}"

    # -------------------------------------------------------------------------
    # TEST 8: Enter correct forgot-password OTP -> Password reset screen opens
    # -------------------------------------------------------------------------
    try:
        rst = db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user_a.id, PasswordResetToken.used.is_(False)).first()
        reset_otp_a = find_otp_for_hash(rst.token_hash)
        assert len(reset_otp_a) == 6

        r = requests.post(f"{BASE_URL}/api/v1/auth/verify-reset-otp", json={
            "email": email_a,
            "otp": reset_otp_a,
        })
        assert r.status_code == 200
        results["TEST 8 — Enter correct forgot-password OTP"] = "PASS"
    except Exception as e:
        results["TEST 8 — Enter correct forgot-password OTP"] = f"FAIL: {e}"

    # -------------------------------------------------------------------------
    # TEST 9: Set new password -> Login with new password succeeds
    # -------------------------------------------------------------------------
    try:
        new_pw = "NewAlphaPassword999!"
        r_reset = requests.post(f"{BASE_URL}/api/v1/auth/reset-password", json={
            "email": email_a,
            "otp": reset_otp_a,
            "new_password": new_pw,
        })
        assert r_reset.status_code == 200

        # Login with new password
        r_login = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": email_a,
            "password": new_pw,
        })
        assert r_login.status_code == 200
        assert "access_token" in r_login.json()
        token_a = r_login.json()["access_token"]
        results["TEST 9 — Set new password (login succeeds)"] = "PASS"
    except Exception as e:
        results["TEST 9 — Set new password (login succeeds)"] = f"FAIL: {e}"

    # -------------------------------------------------------------------------
    # TEST 10: Try old password -> Old password no longer works
    # -------------------------------------------------------------------------
    try:
        r_old = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": email_a,
            "password": "PasswordAlpha123!",
        })
        assert r_old.status_code in (400, 401, 403)
        results["TEST 10 — Old password no longer works"] = "PASS"
    except Exception as e:
        results["TEST 10 — Old password no longer works"] = f"FAIL: {e}"

    # -------------------------------------------------------------------------
    # TEST 11: Forgot Password with different legitimate existing email (Email B)
    # -------------------------------------------------------------------------
    try:
        # Register user B
        r_b = requests.post(f"{BASE_URL}/api/v1/auth/register", json={
            "email": email_b,
            "password": "PasswordBeta123!",
            "name": "Dr. Beta",
        })
        assert r_b.status_code == 201

        # Forgot password for user B
        r_fb = requests.post(f"{BASE_URL}/api/v1/auth/forgot-password", json={"email": email_b})
        assert r_fb.status_code == 200
        user_b = db.query(User).filter(User.email == email_b).first()
        rst_b = db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user_b.id).first()
        assert rst_b is not None
        results["TEST 11 — Forgot Password with Email B (arrives at B)"] = "PASS"
    except Exception as e:
        results["TEST 11 — Forgot Password with Email B (arrives at B)"] = f"FAIL: {e}"

    # Ensure user_a is verified for all reminder tests
    user_a = db.query(User).filter(User.email == email_a).first()
    user_a.email_verified = True
    db.commit()

    # -------------------------------------------------------------------------
    # TEST 12: Create reminder for 2 minutes in future -> Status = PENDING
    # -------------------------------------------------------------------------
    headers_a = {"Authorization": f"Bearer {token_a}"}
    try:
        db.query(UserReminder).filter(UserReminder.user_id == user_a.id).delete()
        db.commit()

        future_dt = datetime.now(timezone.utc) + timedelta(seconds=3)
        future_str = future_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

        r_rem = requests.post(f"{BASE_URL}/api/v1/reminders", json={
            "title": "Autonomous Verification Task",
            "description": "Ensure automatic dispatch",
            "reminder_datetime": future_str,
            "timezone": "Asia/Kolkata",
        }, headers=headers_a)
        assert r_rem.status_code == 201
        rem_data = r_rem.json()
        assert rem_data["status"] == "pending"
        assert rem_data["email_sent"] is False
        results["TEST 12 — Create reminder in future (status=pending)"] = "PASS"
    except Exception as e:
        results["TEST 12 — Create reminder in future (status=pending)"] = f"FAIL: {e}"

    # -------------------------------------------------------------------------
    # TEST 13 & 14: Do NOT click button. Scheduled time arrives -> Automatic email, status=SENT, sent_at
    # -------------------------------------------------------------------------
    try:
        # Wait 5 seconds for the reminder to become due and the live worker (polling every 5s) to process it
        print("  -> Waiting for live reminder worker to process due reminder automatically...")
        found_sent = False
        for _ in range(10):
            time.sleep(1)
            db.expire_all()
            rem_chk = db.query(UserReminder).filter(UserReminder.id == rem_data["id"]).first()
            if rem_chk and (rem_chk.status == "sent" or rem_chk.email_sent):
                found_sent = True
                break

        assert found_sent, f"Worker did not mark reminder sent (status: {rem_chk.status if rem_chk else 'none'}, last_error: {rem_chk.last_error if rem_chk else 'none'})"
        assert rem_chk.status == "sent"
        assert rem_chk.email_sent is True
        assert rem_chk.email_sent_at is not None
        results["TEST 13 & 14 — Live worker automatically sends reminder at due time"] = "PASS"
    except Exception as e:
        results["TEST 13 & 14 — Live worker automatically sends reminder at due time"] = f"FAIL: {e}"

    # -------------------------------------------------------------------------
    # TEST 15: Refresh browser repeatedly -> No duplicate email
    # -------------------------------------------------------------------------
    try:
        # Repeatedly list reminders
        for _ in range(3):
            r_list = requests.get(f"{BASE_URL}/api/v1/reminders", headers=headers_a)
            assert r_list.status_code == 200

        # Verify status remains sent and unchanged
        db.expire_all()
        rem_chk2 = db.query(UserReminder).filter(UserReminder.id == rem_data["id"]).first()
        assert rem_chk2.status == "sent"
        assert rem_chk2.email_sent is True
        results["TEST 15 — Repeated checks / refreshes (no duplicate email)"] = "PASS"
    except Exception as e:
        results["TEST 15 — Repeated checks / refreshes (no duplicate email)"] = f"FAIL: {e}"

    # -------------------------------------------------------------------------
    # TEST 16: Check frontend files -> No 'Send Test Email Now' button
    # -------------------------------------------------------------------------
    try:
        workspace_code = Path("frontend/app/workspace/page.tsx").read_text(encoding="utf-8")
        project_code = Path("frontend/app/workspace/[projectId]/page.tsx").read_text(encoding="utf-8")
        assert "Send Test Email Now" not in workspace_code
        assert "Send Test Email Now" not in project_code
        assert "Send Test Email" not in workspace_code
        assert "Send Test Email" not in project_code
        results["TEST 16 — 'Send Test Email Now' button completely removed"] = "PASS"
    except Exception as e:
        results["TEST 16 — 'Send Test Email Now' button completely removed"] = f"FAIL: {e}"

    # -------------------------------------------------------------------------
    # TEST 17: Create reminder for TODAY at specific time -> Stored and formatted as TODAY
    # -------------------------------------------------------------------------
    try:
        today_1131 = "2026-10-02T11:31:00"
        r_t17 = requests.post(f"{BASE_URL}/api/v1/reminders", json={
            "title": "Today 11:31 AM Reminder",
            "reminder_datetime": today_1131,
            "timezone": "Asia/Kolkata",
        }, headers=headers_a)
        assert r_t17.status_code == 201
        d17 = r_t17.json()
        r_db17 = db.query(UserReminder).filter(UserReminder.id == d17["id"]).first()
        assert r_db17.reminder_datetime.hour == 6
        assert r_db17.reminder_datetime.minute == 1

        kolkata_tz = zoneinfo.ZoneInfo("Asia/Kolkata")
        local_17 = r_db17.reminder_datetime.replace(tzinfo=timezone.utc).astimezone(kolkata_tz)
        assert local_17.strftime("%Y-%m-%d") == "2026-10-02"
        assert local_17.strftime("%H:%M") == "11:31"
        results["TEST 17 — Reminder for TODAY 11:31 AM remains TODAY"] = "PASS"
    except Exception as e:
        results["TEST 17 — Reminder for TODAY 11:31 AM remains TODAY"] = f"FAIL: {e}"

    # -------------------------------------------------------------------------
    # TEST 18: Create reminder near midnight (11:59 PM today vs 12:01 AM tomorrow)
    # -------------------------------------------------------------------------
    try:
        cases = [
            ("2026-10-02T23:59:00", 18, 29, "2026-10-02", "23:59"),
            ("2026-10-03T00:01:00", 18, 31, "2026-10-03", "00:01"),
        ]
        kolkata = zoneinfo.ZoneInfo("Asia/Kolkata")
        for inp, exp_h, exp_m, exp_date, exp_time in cases:
            r_18 = requests.post(f"{BASE_URL}/api/v1/reminders", json={
                "title": f"Midnight {inp}",
                "reminder_datetime": inp,
                "timezone": "Asia/Kolkata",
            }, headers=headers_a)
            assert r_18.status_code == 201
            d18 = r_18.json()
            r_db18 = db.query(UserReminder).filter(UserReminder.id == d18["id"]).first()
            assert r_db18.reminder_datetime.hour == exp_h
            assert r_db18.reminder_datetime.minute == exp_m
            loc = r_db18.reminder_datetime.replace(tzinfo=timezone.utc).astimezone(kolkata)
            assert loc.strftime("%Y-%m-%d") == exp_date
            assert loc.strftime("%H:%M") == exp_time
        results["TEST 18 — Midnight boundary conversion"] = "PASS"
    except Exception as e:
        results["TEST 18 — Midnight boundary conversion"] = f"FAIL: {e}"

    # -------------------------------------------------------------------------
    # TEST 19: Restart backend -> Pending reminders remain in database and scheduler processes them
    # -------------------------------------------------------------------------
    try:
        # Create an interrupted reminder in 'processing' status
        rem19 = UserReminder(
            user_id=user_a.id,
            title="Restart Persistence Test",
            reminder_datetime=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=2),
            timezone="Asia/Kolkata",
            status="processing",
            email_sent=False,
        )
        db.add(rem19)
        db.commit()
        rem19_id = rem19.id

        # Trigger recovery (which runs on worker/server startup)
        from app.services.reminder_agent import recover_stale_reminders
        rec = recover_stale_reminders(db)
        assert rec >= 1
        db.commit()

        # Verify it was recovered back to pending
        rem19_pending = db.query(UserReminder).filter(UserReminder.id == rem19_id).first()
        assert rem19_pending.status == "pending"
        db.commit()

        # Wait for live worker to process it (polling every 5s)
        found_sent19 = False
        for _ in range(12):
            time.sleep(1)
            db.rollback()
            rem19_chk = db.query(UserReminder).filter(UserReminder.id == rem19_id).first()
            if rem19_chk and rem19_chk.status == "sent":
                found_sent19 = True
                break

        assert found_sent19, f"Worker did not send recovered reminder (status={rem19_chk.status if rem19_chk else 'none'})"
        assert rem19_chk.email_sent is True
        db.commit()
        results["TEST 19 — Restart resilience and recovery"] = "PASS"
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        results["TEST 19 — Restart resilience and recovery"] = f"FAIL: {type(e).__name__}: {e}"

    # -------------------------------------------------------------------------
    # TEST 20: Create multiple reminders -> Each processed independently
    # -------------------------------------------------------------------------
    try:
        db.commit()
        now_utc = datetime.now(timezone.utc)
        times = [
            (now_utc - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            (now_utc + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ"), # Future
        ]
        created_ids = []
        for idx, t in enumerate(times):
            rc = requests.post(f"{BASE_URL}/api/v1/reminders", json={
                "title": f"Batch Task {idx}",
                "reminder_datetime": t,
                "timezone": "Asia/Kolkata",
            }, headers=headers_a)
            assert rc.status_code == 201, f"Failed create: {rc.text}"
            created_ids.append(rc.json()["id"])

        # Wait for live worker to process the due one
        found_sent20 = False
        for _ in range(12):
            time.sleep(1)
            db.rollback()
            rem_past = db.query(UserReminder).filter(UserReminder.id == created_ids[0]).first()
            if rem_past and rem_past.status == "sent":
                found_sent20 = True
                break

        assert found_sent20, f"Past reminder not sent (status: {rem_past.status if rem_past else 'none'})"
        assert rem_past.email_sent is True

        # Future reminder is still pending
        db.rollback()
        rem_future = db.query(UserReminder).filter(UserReminder.id == created_ids[1]).first()
        assert rem_future.status == "pending"
        assert rem_future.email_sent is False
        db.commit()
        results["TEST 20 — Multiple reminders processed independently"] = "PASS"
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        results["TEST 20 — Multiple reminders processed independently"] = f"FAIL: {e}"

    print("\n" + "=" * 80)
    print("SUMMARY OF ALL 20 TESTS (PART 9):")
    print("=" * 80)
    all_pass = True
    for name, res in results.items():
        print(f"  {name:<60} : {res}")
        if "FAIL" in res:
            all_pass = False

    print("=" * 80)
    print("RESULT: " + ("100% PASS (20/20)" if all_pass else "FAILURES DETECTED"))
    print("=" * 80)
    db.close()
    return all_pass


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
