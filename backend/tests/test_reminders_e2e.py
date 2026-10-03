import zoneinfo
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.db.models import User, UserReminder
from app.main import app
from app.services.reminder_agent import process_due_reminders, recover_stale_reminders
from conftest import TestingSessionLocal


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def clean_reminders(db_session):
    db_session.query(UserReminder).delete()
    db_session.commit()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def verified_user(db_session):
    user = User(
        email="verified_researcher@example.com",
        name="Dr. Verified",
        password_hash="dummy_password_hash",
        email_verified=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def unverified_user(db_session):
    user = User(
        email="unverified_researcher@example.com",
        name="Unverified User",
        password_hash="dummy_password_hash",
        email_verified=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def verified_user_token(verified_user):
    return create_access_token(str(verified_user.id))


@pytest.fixture
def unverified_user_token(unverified_user):
    return create_access_token(str(unverified_user.id))


def test_reminder_timezone_and_exact_datetime_handling(client, verified_user, verified_user_token, db_session):
    """Test timezone conversion: IST input -> UTC in DB -> serialized with UTC indicator."""
    headers = {"Authorization": f"Bearer {verified_user_token}"}

    # 2026-10-02 10:00:00 in Asia/Kolkata (UTC+5:30) is 2026-10-02 04:30:00 UTC
    payload = {
        "title": "NeurIPS Camera-Ready Submission",
        "description": "Finalize camera-ready PDF and submit to OpenReview",
        "reminder_datetime": "2026-10-02T10:00:00",
        "timezone": "Asia/Kolkata",
    }

    response = client.post("/api/v1/reminders", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    data = response.json()

    assert data["title"] == payload["title"]
    assert data["timezone"] == "Asia/Kolkata"
    assert data["status"] == "pending"
    assert data["email_sent"] is False

    # Check DB representation
    reminder_id = data["id"]
    db_reminder = db_session.query(UserReminder).filter(UserReminder.id == reminder_id).first()
    assert db_reminder is not None
    # In DB it must be stored as 04:30:00 UTC
    assert db_reminder.reminder_datetime.hour == 4
    assert db_reminder.reminder_datetime.minute == 30
    assert db_reminder.timezone == "Asia/Kolkata"


def test_duplicate_prevention_exactly_one_email(client, verified_user, verified_user_token, db_session):
    """Test that atomic locking ensures exactly ONE email is sent even if scheduler runs multiple times."""
    headers = {"Authorization": f"Bearer {verified_user_token}"}

    past_time = (datetime.now(timezone.utc) - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = {
        "title": "Synthesize Literature Review Matrix",
        "description": "Complete Section 3 comparative table",
        "reminder_datetime": past_time,
        "timezone": "UTC",
    }

    create_res = client.post("/api/v1/reminders", json=payload, headers=headers)
    assert create_res.status_code == 201
    reminder_id = create_res.json()["id"]

    # Run scheduler pass 1: should process exactly 1 reminder
    processed_first = process_due_reminders(db_session)
    assert processed_first == 1

    db_session.expire_all()
    rem = db_session.query(UserReminder).filter(UserReminder.id == reminder_id).first()
    assert rem.status == "sent"
    assert rem.email_sent is True
    assert rem.email_sent_at is not None

    # Run scheduler pass 2 immediately: must NOT send duplicate email
    processed_second = process_due_reminders(db_session)
    assert processed_second == 0


def test_reminder_cancellation(client, verified_user, verified_user_token, db_session):
    """Test that cancelling a reminder stops the scheduler from dispatching it."""
    headers = {"Authorization": f"Bearer {verified_user_token}"}

    past_time = (datetime.now(timezone.utc) - timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = {
        "title": "Lab Group Meeting",
        "description": "Weekly sync on Graph Transformers",
        "reminder_datetime": past_time,
        "timezone": "UTC",
    }

    create_res = client.post("/api/v1/reminders", json=payload, headers=headers)
    assert create_res.status_code == 201
    reminder_id = create_res.json()["id"]

    # Cancel the reminder
    cancel_res = client.post(f"/api/v1/reminders/{reminder_id}/cancel", headers=headers)
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "cancelled"

    # Run scheduler: should NOT process cancelled reminder
    processed = process_due_reminders(db_session)
    assert processed == 0

    db_session.expire_all()
    rem = db_session.query(UserReminder).filter(UserReminder.id == reminder_id).first()
    assert rem.status == "cancelled"
    assert rem.email_sent is False


def test_reminder_editing_and_rescheduling(client, verified_user, verified_user_token, db_session):
    """Test editing a reminder and rescheduling to a future date resets pending status."""
    headers = {"Authorization": f"Bearer {verified_user_token}"}

    past_time = (datetime.now(timezone.utc) - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
    create_res = client.post(
        "/api/v1/reminders",
        json={"title": "Draft Introduction", "reminder_datetime": past_time, "timezone": "UTC"},
        headers=headers,
    )
    reminder_id = create_res.json()["id"]

    # Mark it as sent by processing
    assert process_due_reminders(db_session) == 1

    # Now user edits it with a new future time and title
    future_time = (datetime.now(timezone.utc) + timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
    update_res = client.patch(
        f"/api/v1/reminders/{reminder_id}",
        json={
            "title": "Draft Introduction (Rescheduled)",
            "reminder_datetime": future_time,
        },
        headers=headers,
    )
    assert update_res.status_code == 200
    updated_data = update_res.json()
    assert updated_data["title"] == "Draft Introduction (Rescheduled)"
    assert updated_data["status"] == "pending"
    assert updated_data["email_sent"] is False

    # Process now: should NOT send because it is in the future
    assert process_due_reminders(db_session) == 0


def test_backend_restart_resilience(client, verified_user, verified_user_token):
    """Test that persisted reminders survive restart and are detected by new sessions."""
    headers = {"Authorization": f"Bearer {verified_user_token}"}

    past_time = (datetime.now(timezone.utc) - timedelta(minutes=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    create_res = client.post(
        "/api/v1/reminders",
        json={"title": "Restart Test Reminder", "reminder_datetime": past_time, "timezone": "UTC"},
        headers=headers,
    )
    assert create_res.status_code == 201
    reminder_id = create_res.json()["id"]

    # Simulate fresh backend session
    fresh_session = TestingSessionLocal()
    try:
        processed = process_due_reminders(fresh_session)
        assert processed >= 1
        rem = fresh_session.query(UserReminder).filter(UserReminder.id == reminder_id).first()
        assert rem.status == "sent"
        assert rem.email_sent is True
    finally:
        fresh_session.close()


def test_multiple_reminders_ordering(client, verified_user, verified_user_token, db_session):
    """Test that multiple reminders are ordered chronologically and processed."""
    headers = {"Authorization": f"Bearer {verified_user_token}"}
    now = datetime.now(timezone.utc)

    times = [
        (now - timedelta(minutes=15)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        (now - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        (now - timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%SZ"),
    ]

    for i, t in enumerate(times):
        client.post(
            "/api/v1/reminders",
            json={"title": f"Task {i}", "reminder_datetime": t, "timezone": "UTC"},
            headers=headers,
        )

    list_res = client.get("/api/v1/reminders", headers=headers)
    assert list_res.status_code == 200
    items = list_res.json()
    assert len(items) >= 3
    # Check ascending order
    for idx in range(len(items) - 1):
        assert items[idx]["reminder_datetime"] <= items[idx + 1]["reminder_datetime"]

    # All 3 are due and should process successfully
    processed = process_due_reminders(db_session)
    assert processed == 3


def test_user_isolation(client, verified_user, verified_user_token, unverified_user_token):
    """Test that User A cannot view, edit, or cancel User B's reminders."""
    headers_user_a = {"Authorization": f"Bearer {verified_user_token}"}
    headers_user_b = {"Authorization": f"Bearer {unverified_user_token}"}

    create_res = client.post(
        "/api/v1/reminders",
        json={"title": "Private Task A", "reminder_datetime": "2026-10-02T12:00:00Z"},
        headers=headers_user_a,
    )
    reminder_id = create_res.json()["id"]

    # User B attempts to access User A's reminder
    get_res = client.get(f"/api/v1/reminders/{reminder_id}", headers=headers_user_b)
    assert get_res.status_code == 404

    # User B attempts to cancel User A's reminder
    cancel_res = client.post(f"/api/v1/reminders/{reminder_id}/cancel", headers=headers_user_b)
    assert cancel_res.status_code == 404

    # User B attempts to edit User A's reminder
    patch_res = client.patch(f"/api/v1/reminders/{reminder_id}", json={"title": "Hacked"}, headers=headers_user_b)
    assert patch_res.status_code == 404


def test_unverified_email_protection(client, unverified_user, unverified_user_token, db_session):
    """Test that reminders are NOT sent to unverified emails and are postponed safely."""
    headers = {"Authorization": f"Bearer {unverified_user_token}"}

    past_time = (datetime.now(timezone.utc) - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
    create_res = client.post(
        "/api/v1/reminders",
        json={"title": "Unverified User Task", "reminder_datetime": past_time, "timezone": "UTC"},
        headers=headers,
    )
    assert create_res.status_code == 201
    reminder_id = create_res.json()["id"]

    processed = process_due_reminders(db_session)
    assert processed == 0

    db_session.expire_all()
    rem = db_session.query(UserReminder).filter(UserReminder.id == reminder_id).first()
    assert rem.status == "pending"
    assert rem.email_sent is False
    assert "not verified" in (rem.last_error or "")


def test_stale_reminder_recovery_on_startup(verified_user, db_session):
    """Test that a reminder left in 'processing' state (e.g. from an ungraceful server crash) is reset to 'pending'."""
    stale_reminder = UserReminder(
        user_id=verified_user.id,
        title="Interrupted Reminder",
        reminder_datetime=datetime.now(timezone.utc) - timedelta(minutes=10),
        status="processing",
        email_sent=False,
    )
    db_session.add(stale_reminder)
    db_session.commit()
    db_session.refresh(stale_reminder)

    recovered_count = recover_stale_reminders(db_session)
    assert recovered_count == 1

    db_session.refresh(stale_reminder)
    assert stale_reminder.status == "pending"
    assert "Recovered from interrupted processing" in (stale_reminder.last_error or "")


def test_scheduler_handles_email_failure_gracefully(client, verified_user, verified_user_token, db_session, monkeypatch):
    """Test that if the email provider throws an exception, the reminder is marked pending with last_error, avoiding fatal crash."""
    from app.services import reminder_agent

    def mock_send_email(*args, **kwargs):
        raise ConnectionError("SMTP gateway unreachable")

    monkeypatch.setattr(reminder_agent, "send_email", mock_send_email)

    headers = {"Authorization": f"Bearer {verified_user_token}"}
    past_time = (datetime.now(timezone.utc) - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
    create_res = client.post(
        "/api/v1/reminders",
        json={"title": "Failing Email Reminder", "reminder_datetime": past_time, "timezone": "UTC"},
        headers=headers,
    )
    assert create_res.status_code == 201
    reminder_id = create_res.json()["id"]

    # Run scheduler: must not crash
    processed = process_due_reminders(db_session)
    assert processed == 0

    db_session.expire_all()
    rem = db_session.query(UserReminder).filter(UserReminder.id == reminder_id).first()
    assert rem.status == "pending"
    assert rem.email_sent is False
    assert "SMTP gateway unreachable" in (rem.last_error or "")


def test_date_boundaries_and_midnight_transitions(client, verified_user, verified_user_token, db_session):
    """Test date boundaries: Today 10:00 AM, Today 11:59 PM, Tomorrow 12:01 AM, Tomorrow 10:00 AM in Asia/Kolkata."""
    headers = {"Authorization": f"Bearer {verified_user_token}"}
    kolkata_tz = zoneinfo.ZoneInfo("Asia/Kolkata")

    cases = [
        # (local_input, expected_utc_hour, expected_utc_min, expected_local_date, expected_local_time)
        ("2026-10-02T10:00:00", 4, 30, "2026-10-02", "10:00"),
        ("2026-10-02T23:59:00", 18, 29, "2026-10-02", "23:59"),
        ("2026-10-03T00:01:00", 18, 31, "2026-10-03", "00:01"),
        ("2026-10-03T10:00:00", 4, 30, "2026-10-03", "10:00"),
    ]

    for local_input, exp_utc_h, exp_utc_m, exp_loc_date, exp_loc_time in cases:
        payload = {
            "title": f"Boundary Test {local_input}",
            "reminder_datetime": local_input,
            "timezone": "Asia/Kolkata",
        }
        res = client.post("/api/v1/reminders", json=payload, headers=headers)
        assert res.status_code == 201, res.text
        data = res.json()

        rem_id = data["id"]
        db_rem = db_session.query(UserReminder).filter(UserReminder.id == rem_id).first()
        assert db_rem is not None

        # Verify UTC stored in DB
        assert db_rem.reminder_datetime.hour == exp_utc_h, f"Failed UTC hour for {local_input}"
        assert db_rem.reminder_datetime.minute == exp_utc_m, f"Failed UTC min for {local_input}"

        # Verify conversion back to Asia/Kolkata
        utc_dt = db_rem.reminder_datetime.replace(tzinfo=timezone.utc)
        local_dt = utc_dt.astimezone(kolkata_tz)
        assert local_dt.strftime("%Y-%m-%d") == exp_loc_date, (
            f"Calendar day shifted incorrectly for {local_input}: got {local_dt.strftime('%Y-%m-%d')}, expected {exp_loc_date}"
        )
        assert local_dt.strftime("%H:%M") == exp_loc_time, (
            f"Local time shifted incorrectly for {local_input}: got {local_dt.strftime('%H:%M')}, expected {exp_loc_time}"
        )

        # Verify serialization contains UTC offset
        assert "+00:00" in data["reminder_datetime"] or "Z" in data["reminder_datetime"]


def test_manual_test_email_does_not_disarm_future_reminder(client, verified_user, verified_user_token, db_session, monkeypatch):
    """Test that clicking 'Send Test Email Now' on a future reminder sends a test email but preserves 'pending' status."""
    from app.services import reminder_agent

    mock_send = MagicMock(return_value={"status": "sent"})
    monkeypatch.setattr(reminder_agent, "send_email", mock_send)

    headers = {"Authorization": f"Bearer {verified_user_token}"}

    # Schedule reminder for tomorrow at 10:00 AM Asia/Kolkata
    tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
    future_time_str = tomorrow.strftime("%Y-%m-%dT10:00:00")
    create_res = client.post(
        "/api/v1/reminders",
        json={
            "title": "Future Grant Deadline",
            "reminder_datetime": future_time_str,
            "timezone": "Asia/Kolkata",
        },
        headers=headers,
    )
    assert create_res.status_code == 201
    reminder_id = create_res.json()["id"]

    # 1. User clicks "Send Test Email Now"
    test_send_res = client.post(f"/api/v1/reminders/{reminder_id}/send-now", headers=headers)
    assert test_send_res.status_code == 200
    test_data = test_send_res.json()

    # Test email was sent via email service with [Test Email] prefix
    assert mock_send.call_count == 1
    call_args = mock_send.call_args[0]
    assert "[Test Email]" in call_args[1]  # subject

    # Crucial: Reminder status must STILL be pending and email_sent must STILL be False
    assert test_data["status"] == "pending"
    assert test_data["email_sent"] is False
    assert "Test email sent successfully" in (test_data["last_error"] or "")

    # 2. Scheduler runs at current time: should NOT process future reminder
    processed_current = process_due_reminders(db_session, now=datetime.now(timezone.utc) - timedelta(hours=1))
    assert processed_current == 0

    # 3. Time advances to due date: Scheduler processes the reminder automatically!
    mock_send.reset_mock()
    rem = db_session.query(UserReminder).filter(UserReminder.id == reminder_id).first()
    future_due_utc = rem.reminder_datetime.replace(tzinfo=timezone.utc) + timedelta(seconds=1)
    processed_due = process_due_reminders(db_session, now=future_due_utc)
    assert processed_due == 1

    # Scheduled email was sent (WITHOUT [Test Email] prefix)
    assert mock_send.call_count == 1
    call_args_due = mock_send.call_args[0]
    assert "[Test Email]" not in call_args_due[1]

    # DB state is now sent
    db_session.expire_all()
    rem = db_session.query(UserReminder).filter(UserReminder.id == reminder_id).first()
    assert rem.status == "sent"
    assert rem.email_sent is True
    assert rem.email_sent_at is not None

    # 4. Duplicate prevention: second pass sends 0
    processed_duplicate = process_due_reminders(db_session, now=future_due_utc)
    assert processed_duplicate == 0
