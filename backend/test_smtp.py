"""
Standalone SMTP test script for ResearchOS.

Run this to verify your SMTP configuration without starting the full server.

Usage (from the backend/ directory):
    python test_smtp.py                          # Test connection only
    python test_smtp.py youremail@gmail.com      # Send a test email

This script reads backend/.env using the same pydantic-settings configuration
as the main application.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure backend/ is on the path so app.* imports work
_backend_dir = Path(__file__).resolve().parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from app.core.config import settings
from app.services.email_service import send_email, test_smtp_connection


def main() -> None:
    print("=" * 60)
    print("  ResearchOS SMTP Configuration Test")
    print("=" * 60)
    print()

    # Show current config (never show password)
    print("Current configuration:")
    print(f"  EMAIL_PROVIDER : {settings.email_provider}")
    print(f"  SMTP_HOST      : {settings.smtp_host or '(not set)'}")
    print(f"  SMTP_PORT      : {settings.smtp_port}")
    print(f"  SMTP_USERNAME  : {settings.smtp_username or '(not set)'}")
    print(f"  SMTP_PASSWORD  : {'****' if settings.smtp_password else '(not set)'}")
    print(f"  SMTP_FROM      : {settings.smtp_from or settings.email_from}")
    print(f"  Config file    : {Path(settings.model_config.get('env_file', '.env'))}")
    print()

    # Test connection
    print("Testing SMTP connection and authentication...")
    print("-" * 60)
    result = test_smtp_connection()

    for key, value in result.items():
        print(f"  {key:20s}: {value}")
    print("-" * 60)
    print()

    if result.get("status") == "ok":
        print("✓ SMTP connection and authentication: OK")
    else:
        print(f"✗ SMTP test failed: {result.get('detail', 'Unknown error')}")
        if "guidance" in result:
            print()
            print("Provider-specific guidance:")
            for line in result["guidance"].split("\n"):
                print(f"  {line}")
        print()
        print("Check your backend/.env file and fix the configuration above.")
        sys.exit(1)

    # If a recipient email was provided, send a test email
    recipient = sys.argv[1] if len(sys.argv) > 1 else None
    if recipient:
        print()
        print(f"Sending test email to {recipient}...")
        send_result = send_email(
            recipient,
            "ResearchOS — SMTP Test",
            "This is a test email from ResearchOS.\n\n"
            "If you received this, your SMTP configuration is working correctly.",
        )
        print(f"  Status: {send_result.get('status', 'unknown')}")
        print(f"  Detail: {send_result.get('detail', '')}")

        if send_result.get("status") == "sent":
            print()
            print(f"✓ Test email sent to {recipient}!")
            print("  Check your inbox (and spam folder).")
        else:
            print()
            print(f"✗ Failed to send test email: {send_result.get('detail')}")
            sys.exit(1)
    else:
        print("To send a test email, run:")
        print(f"  python {Path(__file__).name} youremail@example.com")

    print()
    print("=" * 60)
    print("  Done")
    print("=" * 60)


if __name__ == "__main__":
    main()
