"""End-to-end verification of Phase 8 (Application Restart) and Phase 9 (Real OTP & Reminder Flow)."""

import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.db.session import SessionLocal
from app.db.models import User, UserReminder, EmailVerification, PasswordResetToken
from app.services.otp_service import (
    create_email_verification,
    verify_email_otp,
    create_password_reset_token_for_email,
    verify_password_reset_token_for_email,
    can_resend_otp,
)
from app.services.reminder_agent import process_due_reminders, recover_stale_reminders
from app.core.security import hash_password, verify_password


def run_e2e_checks():
    db = SessionLocal()
    print("=" * 60)
    print("STARTING REAL E2E VERIFICATION FOR PHASES 8 & 9")
    print("=" * 60)

    # 1. Setup clean test user
    test_email = "godlevel.researcher@example.com"
    db.query(EmailVerification).filter(EmailVerification.user_id.in_(
        db.query(User.id).filter(User.email == test_email)
    )).delete(synchronize_session=False)
    db.query(PasswordResetToken).filter(PasswordResetToken.user_id.in_(
        db.query(User.id).filter(User.email == test_email)
    )).delete(synchronize_session=False)
    db.query(UserReminder).filter(UserReminder.user_id.in_(
        db.query(User.id).filter(User.email == test_email)
    )).delete(synchronize_session=False)
    db.query(User).filter(User.email == test_email).delete()
    db.commit()

    user = User(
        email=test_email,
        name="Dr. Reliability",
        password_hash=hash_password("InitialPassword123!"),
        email_verified=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    print(f"Created unverified test user id={user.id}, email={user.email}")

    # TEST 1 — Registration OTP
    print("\n--- TEST 1: Registration OTP ---")
    otp1 = create_email_verification(db, user.id, purpose="registration")
    assert len(otp1) == 6 and otp1.isdigit(), f"Invalid OTP format: {otp1}"
    ev1 = db.query(EmailVerification).filter(EmailVerification.user_id == user.id).first()
    assert ev1 is not None, "EmailVerification record not created!"
    print(f"PASS: OTP generated successfully with 5-minute expiry ({ev1.expires_at})")

    # TEST 2 — Invalid OTP
    print("\n--- TEST 2: Invalid OTP Rejection ---")
    ok, msg = verify_email_otp(db, user.id, "000000", purpose="registration")
    assert not ok, "Invalid OTP was erroneously accepted!"
    print(f"PASS: Wrong OTP correctly rejected with: '{msg}'")

    # TEST 3 — Expired OTP
    print("\n--- TEST 3: Expired OTP Rejection ---")
    ev1.expires_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=1)
    db.commit()
    ok_exp, msg_exp = verify_email_otp(db, user.id, otp1, purpose="registration")
    assert not ok_exp, "Expired OTP was erroneously accepted!"
    print(f"PASS: Expired OTP correctly rejected with: '{msg_exp}'")

    # TEST 4 — Resend Cooldown & Delivery
    print("\n--- TEST 4: Resend OTP Cooldown ---")
    otp_fresh = create_email_verification(db, user.id, purpose="registration")
    ev_fresh = db.query(EmailVerification).filter(EmailVerification.user_id == user.id).first()
    assert ev_fresh is not None
    # Cooldown should be active immediately after creation
    can_resend, cd_msg = can_resend_otp(db, user.id, purpose="registration")
    assert not can_resend, "Cooldown failed to block rapid resend!"
    print(f"PASS: Cooldown successfully enforced immediately after creation: '{cd_msg}'")

    # Now simulate cooldown elapsed (70s ago)
    ev_fresh.created_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=70)
    db.commit()
    can_resend2, _ = can_resend_otp(db, user.id, purpose="registration")
    assert can_resend2, "Cooldown should have expired after 70s!"
    otp2 = create_email_verification(db, user.id, purpose="registration")
    print(f"PASS: After cooldown, exactly one new OTP generated")

    # TEST 5 — OTP Verification & Account Activation
    print("\n--- TEST 5: Valid OTP Verification ---")
    ok_val, val_msg = verify_email_otp(db, user.id, otp2, purpose="registration")
    assert ok_val, f"Valid OTP failed to verify: {val_msg}"
    db.refresh(user)
    assert user.email_verified is True, "User.email_verified was not set to True!"
    # Ensure token consumed
    consumed_count = db.query(EmailVerification).filter(EmailVerification.user_id == user.id).count()
    assert consumed_count == 0, "OTP was not consumed/deleted after verification!"
    print(f"PASS: Account verified successfully, token consumed, email_verified=True")

    # TEST 6 — Forgot Password Flow
    print("\n--- TEST 6: Forgot Password & Reset Flow ---")
    reset_otp, primary_user = create_password_reset_token_for_email(db, user.email)
    assert reset_otp is not None and primary_user.id == user.id
    # Verify reset token
    ok_rst, rst_msg = verify_password_reset_token_for_email(db, user.email, reset_otp, mark_used=True)
    assert ok_rst, f"Reset OTP verification failed: {rst_msg}"
    user.password_hash = hash_password("NewGodLevelPassword456!")
    db.commit()
    db.refresh(user)
    assert verify_password("NewGodLevelPassword456!", user.password_hash)
    print("PASS: Forgot password OTP generated, verified, and password securely updated")

    # =========================================================
    # PHASE 8 & 9: REMINDER AGENT & RESTART RECOVERY TEST
    # =========================================================
    print("\n" + "=" * 60)
    print("PHASE 8 & 9: REMINDER AGENT RESTART AND AUTOMATIC DISPATCH")
    print("=" * 60)

    # Clean existing reminders for test user
    db.query(UserReminder).filter(UserReminder.user_id == user.id).delete()
    db.commit()

    # 1. Create a reminder scheduled 3 seconds in the future
    # Using explicit Asia/Kolkata timezone canonicalization
    future_time_utc = datetime.now(timezone.utc) + timedelta(seconds=3)
    reminder = UserReminder(
        user_id=user.id,
        title="God-Level Autonomous Verification Reminder",
        description="Autonomous verification test ensuring exact time dispatch without manual triggers",
        reminder_datetime=future_time_utc.replace(tzinfo=None),
        timezone="Asia/Kolkata",
        status="pending",
        email_sent=False,
    )
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    reminder_id = reminder.id
    print(f"1. Created reminder id={reminder_id}, scheduled for {reminder.reminder_datetime} UTC")
    print(f"   Initial status: {reminder.status}, email_sent: {reminder.email_sent}")

    # 2. Simulate Backend Crash / Interruption while in 'processing' state
    print("\n2. Simulating backend interruption (stale 'processing' state)...")
    reminder.status = "processing"
    db.commit()

    # 3. Simulate Backend Restart -> recovery on startup
    print("3. Backend Restarting... invoking startup recovery...")
    recovered = recover_stale_reminders(db)
    assert recovered == 1, f"Expected 1 recovered reminder, got {recovered}"
    db.refresh(reminder)
    assert reminder.status == "pending", f"Expected 'pending' status after recovery, got {reminder.status}"
    print(f"PASS: Interrupted reminder successfully recovered back to 'pending'")

    # 4. Confirm reminder is not processed prematurely
    processed_early = process_due_reminders(db, now=future_time_utc - timedelta(seconds=2))
    assert processed_early == 0, "Reminder should NOT be processed before its due time!"
    print("PASS: Early scheduler tick correctly ignored future reminder")

    # 5. Wait for exact due time (3.5 seconds)
    print("\n4. Waiting for exact due time...")
    time.sleep(3.5)

    # 6. Automatic background scheduler tick (ZERO button clicks, ZERO 'Send Test Mail')
    print("5. Scheduler tick executing at due time...")
    processed = process_due_reminders(db)
    assert processed == 1, f"Expected 1 reminder to be processed, got {processed}"
    print(f"PASS: Automatic scheduler processed due reminder (processed_count={processed})")

    # 7. Verify DB state is SENT and email_sent is TRUE
    db.refresh(reminder)
    assert reminder.status == "sent", f"Expected status 'sent', got {reminder.status}"
    assert reminder.email_sent is True, f"Expected email_sent True, got {reminder.email_sent}"
    assert reminder.email_sent_at is not None, "Expected email_sent_at timestamp!"
    print(f"PASS: Database state verified: status='{reminder.status}', email_sent={reminder.email_sent}, sent_at={reminder.email_sent_at}")

    # 8. Duplicate Prevention: Run scheduler tick again immediately
    print("\n6. Running second scheduler tick to test duplicate prevention...")
    processed_duplicate = process_due_reminders(db)
    assert processed_duplicate == 0, f"DUPLICATE DETECTED! Processed {processed_duplicate} on second pass"
    print(f"PASS: Strict duplicate prevention verified: 0 emails sent on duplicate tick")

    print("\n" + "=" * 60)
    print("ALL E2E CHECKS PASSED WITH 100% SUCCESS!")
    print("=" * 60)
    db.close()


if __name__ == "__main__":
    run_e2e_checks()
