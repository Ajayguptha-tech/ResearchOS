"""Email service abstraction.

Uses SMTP when configured, falls back to console logging in development.
Credentials are read from pydantic-settings (env_file / environment variables).
"""

from __future__ import annotations

import logging
import smtplib
import socket
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings

logger = logging.getLogger(__name__)


def _smtp_available() -> bool:
    """Check whether SMTP credentials are configured via settings."""
    return bool(settings.smtp_host and settings.smtp_host.strip())


def send_email(to: str, subject: str, body: str, html: str | None = None) -> dict:
    """Send an email via the configured provider.

    *html* is an optional HTML alternative.  When provided the email is sent
    as ``multipart/alternative`` with both plain-text and HTML parts.

    Returns a dict with ``status`` and ``detail`` keys so callers never
    have to catch exceptions for graceful degradation.
    """
    if not to or not to.strip():
        return {"status": "failed", "detail": "No recipient specified"}

    provider = settings.email_provider.strip().lower() if settings.email_provider else "console"

    if provider == "smtp" and _smtp_available():
        return _send_smtp(to, subject, body, html)

    # Default: console / development provider
    return _send_console(to, subject, body)


def _send_smtp(to: str, subject: str, body: str, html: str | None = None) -> dict:
    """Send email via real SMTP."""
    host = settings.smtp_host.strip() if settings.smtp_host else ""
    port = settings.smtp_port
    username = settings.smtp_username.strip() if settings.smtp_username else ""
    password = settings.smtp_password.strip() if settings.smtp_password else ""
    from_addr = (settings.smtp_from.strip() if settings.smtp_from else "") or settings.email_from

    if not host:
        return {"status": "failed", "detail": "SMTP_HOST not configured"}

    if not username:
        return {"status": "failed", "detail": "SMTP_USERNAME not configured. Check backend/.env"}

    if not password:
        return {"status": "failed", "detail": "SMTP_PASSWORD not configured. Check backend/.env"}

    # Log what we're using (NEVER log the password)
    logger.info(
        "[Email] SMTP connecting to %s:%d as '%s' (from: %s)",
        host, port, username, from_addr,
    )

    msg = MIMEMultipart("alternative")
    msg["From"] = from_addr
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    if html:
        msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(host, port, timeout=20) as server:
            server.ehlo()
            if port != 25:
                server.starttls()
                server.ehlo()
            server.login(username, password)
            server.sendmail(from_addr, [to], msg.as_string())
        logger.info("[Email] Sent to %s: %s", to, subject)
        return {"status": "sent", "detail": "Email sent via SMTP"}
    except smtplib.SMTPAuthenticationError as exc:
        # Provide provider-specific guidance based on the host
        guidance = _smtp_auth_guidance(host, exc)
        logger.error(
            "[Email] SMTP AUTH FAILED for user '%s' at %s:%d. "
            "SMTP response: %s\n%s",
            username, host, port, exc, guidance,
        )
        return {
            "status": "failed",
            "detail": (
                f"SMTP authentication failed for user '{username}' at {host}. "
                f"{guidance}"
            ),
        }
    except smtplib.SMTPConnectError as exc:
        logger.error("[Email] SMTP connection to %s:%d failed: %s", host, port, exc)
        return {
            "status": "failed",
            "detail": f"Could not connect to SMTP server {host}:{port}. Check SMTP_HOST and SMTP_PORT.",
        }
    except socket.gaierror as exc:
        logger.error("[Email] DNS resolution failed for %s: %s", host, exc)
        return {
            "status": "failed",
            "detail": f"Could not resolve SMTP host '{host}'. Check SMTP_HOST in backend/.env.",
        }
    except socket.timeout:
        logger.error("[Email] SMTP connection to %s:%d timed out", host, port)
        return {
            "status": "failed",
            "detail": f"Connection to {host}:{port} timed out.",
        }
    except Exception as exc:
        logger.error("[Email] SMTP send failed for %s: %s (%s)", to, exc, type(exc).__name__)
        return {"status": "failed", "detail": f"Email delivery failed: {exc}"}


def _smtp_auth_guidance(host: str, exc: smtplib.SMTPAuthenticationError) -> str:
    """Return provider-specific guidance for authentication failures."""
    host_lower = host.lower()

    if "brevo" in host_lower or "sendinblue" in host_lower:
        return (
            "Brevo SMTP authentication failed. For Brevo:\n"
            "  1. SMTP_USERNAME must be your Brevo account email (the one you log in with)\n"
            "  2. SMTP_PASSWORD must be your SMTP key (NOT your Brevo login password)\n"
            "     Get it from: https://app.brevo.com/smtp (or Settings > SMTP > Keys)\n"
            "  3. SMTP_FROM must be a verified sender in your Brevo account\n"
            "     Verify at: https://app.brevo.com/senders"
        )
    if "gmail" in host_lower:
        return (
            "Gmail SMTP authentication failed. For Gmail:\n"
            "  1. You need a Gmail App Password (NOT your regular password)\n"
            "  2. Enable 2-Step Verification at https://myaccount.google.com/security\n"
            "  3. Create App Password at https://myaccount.google.com/apppasswords\n"
            "  4. Select 'Mail' and 'Other (Custom name)'\n"
            "  5. Use the 16-character generated password as SMTP_PASSWORD"
        )
    if "office365" in host_lower or "outlook" in host_lower:
        return (
            "Outlook SMTP authentication failed. For Microsoft 365:\n"
            "  1. SMTP_USERNAME should be your full email address\n"
            "  2. Use an App Password if 2FA is enabled\n"
            "  3. Verify SMTP access is allowed in your organization's security policy"
        )
    return (
        f"Verify SMTP_USERNAME and SMTP_PASSWORD in backend/.env. "
        f"The username used was '{host}'."
    )


def _send_console(to: str, subject: str, body: str) -> dict:
    """Log the email to the console (development mode)."""
    logger.warning(
        "[Email][DEV] OTP EMAIL (console mode — not sent via SMTP)\n"
        "  To: %s\n"
        "  Subject: %s\n"
        "  ---\n"
        "  %s\n"
        "  ---",
        to,
        subject,
        body.replace("\n", "\n  "),
    )
    return {
        "status": "logged",
        "detail": "OTP printed to backend terminal (EMAIL_PROVIDER=console). "
        "Set EMAIL_PROVIDER=smtp in backend/.env to send real emails.",
    }


# ---------------------------------------------------------------------------
# SMTP diagnostic / test function
# ---------------------------------------------------------------------------

def test_smtp_connection() -> dict:
    """Test SMTP connectivity and authentication without sending an email.

    Returns a dict with diagnostic information.  Never exposes the password.
    """
    host = settings.smtp_host.strip() if settings.smtp_host else ""
    port = settings.smtp_port
    username = settings.smtp_username.strip() if settings.smtp_username else ""
    password = settings.smtp_password.strip() if settings.smtp_password else ""
    from_addr = (settings.smtp_from.strip() if settings.smtp_from else "") or settings.email_from

    result: dict = {
        "email_provider": settings.email_provider,
        "smtp_host": host or "(not set)",
        "smtp_port": port,
        "smtp_username": username or "(not set)",
        "smtp_from": from_addr,
        "smtp_password_set": bool(password),
    }

    if not host:
        result["status"] = "error"
        result["detail"] = "SMTP_HOST is not set in backend/.env"
        return result

    if not username:
        result["status"] = "error"
        result["detail"] = "SMTP_USERNAME is not set in backend/.env"
        return result

    if not password:
        result["status"] = "error"
        result["detail"] = "SMTP_PASSWORD is not set in backend/.env"
        return result

    # Try to connect and authenticate
    try:
        with smtplib.SMTP(host, port, timeout=15) as server:
            server.ehlo()
            result["tls_available"] = False
            if port != 25:
                server.starttls()
                server.ehlo()
                result["tls_available"] = True
            server.login(username, password)
            result["status"] = "ok"
            result["detail"] = f"Successfully connected and authenticated with {host}:{port}"
    except smtplib.SMTPAuthenticationError as exc:
        result["status"] = "auth_failed"
        result["detail"] = f"SMTP authentication failed: {exc}"
        result["guidance"] = _smtp_auth_guidance(host, exc)
    except smtplib.SMTPConnectError as exc:
        result["status"] = "connection_failed"
        result["detail"] = f"Could not connect to {host}:{port}: {exc}"
    except socket.gaierror as exc:
        result["status"] = "dns_failed"
        result["detail"] = f"Could not resolve host '{host}': {exc}"
    except socket.timeout:
        result["status"] = "timeout"
        result["detail"] = f"Connection to {host}:{port} timed out"
    except Exception as exc:
        result["status"] = "error"
        result["detail"] = f"Unexpected error: {exc} ({type(exc).__name__})"

    return result


# ---------------------------------------------------------------------------
# HTML email templates
# ---------------------------------------------------------------------------

def verification_email_html(otp: str) -> str:
    """Return a professional HTML email for OTP verification."""
    return f"""\
<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f4f1fa;font-family:Inter,Helvetica,Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f1fa;padding:40px 20px;">
<tr><td align="center">
<table width="480" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(80,50,160,0.08);">
  <tr><td style="background:linear-gradient(135deg,#6d4fd2,#8d70ed);padding:28px 32px;text-align:center;">
    <span style="font-size:11px;font-weight:700;letter-spacing:0.15em;color:rgba(255,255,255,0.85);text-transform:uppercase;">ResearchOS</span>
  </td></tr>
  <tr><td style="padding:36px 32px 20px;text-align:center;">
    <h1 style="margin:0;font-size:20px;font-weight:700;color:#1b2440;">Verify your email address</h1>
    <p style="margin:12px 0 0;font-size:14px;color:#68728a;line-height:1.6;">Enter the following 6-digit code to verify your account:</p>
  </td></tr>
  <tr><td style="padding:0 32px 28px;text-align:center;">
    <div style="display:inline-block;padding:14px 32px;border-radius:12px;background:#f4f1fa;border:2px solid #e0d9f4;">
      <span style="font-size:28px;font-weight:700;letter-spacing:0.3em;color:#5d42be;font-family:monospace;">{otp}</span>
    </div>
  </td></tr>
  <tr><td style="padding:0 32px 24px;text-align:center;">
    <p style="margin:0;font-size:13px;color:#8790a4;line-height:1.6;">This code expires in <strong style="color:#5d42be;">10 minutes</strong>.</p>
  </td></tr>
  <tr><td style="padding:0 32px 32px;text-align:center;border-top:1px solid #f0edff;">
    <p style="margin:20px 0 0;font-size:12px;color:#a1a9bb;">If you did not create this account, you can safely ignore this email.</p>
  </td></tr>
</table>
</td></tr></table>
</body></html>"""


def password_reset_email_html(otp: str) -> str:
    """Return a professional HTML email for password reset."""
    return f"""\
<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f4f1fa;font-family:Inter,Helvetica,Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f1fa;padding:40px 20px;">
<tr><td align="center">
<table width="480" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(80,50,160,0.08);">
  <tr><td style="background:linear-gradient(135deg,#6d4fd2,#8d70ed);padding:28px 32px;text-align:center;">
    <span style="font-size:11px;font-weight:700;letter-spacing:0.15em;color:rgba(255,255,255,0.85);text-transform:uppercase;">ResearchOS</span>
  </td></tr>
  <tr><td style="padding:36px 32px 20px;text-align:center;">
    <h1 style="margin:0;font-size:20px;font-weight:700;color:#1b2440;">Reset your password</h1>
    <p style="margin:12px 0 0;font-size:14px;color:#68728a;line-height:1.6;">We received a password reset request. Use the code below:</p>
  </td></tr>
  <tr><td style="padding:0 32px 28px;text-align:center;">
    <div style="display:inline-block;padding:14px 32px;border-radius:12px;background:#f4f1fa;border:2px solid #e0d9f4;">
      <span style="font-size:28px;font-weight:700;letter-spacing:0.3em;color:#5d42be;font-family:monospace;">{otp}</span>
    </div>
  </td></tr>
  <tr><td style="padding:0 32px 24px;text-align:center;">
    <p style="margin:0;font-size:13px;color:#8790a4;line-height:1.6;">This code expires in <strong style="color:#5d42be;">10 minutes</strong>.</p>
  </td></tr>
  <tr><td style="padding:0 32px 32px;text-align:center;border-top:1px solid #f0edff;">
    <p style="margin:20px 0 0;font-size:12px;color:#a1a9bb;">If you did not request a password reset, you can safely ignore this email.</p>
  </td></tr>
</table>
</td></tr></table>
</body></html>"""


def verification_email_body(otp: str) -> str:
    """Return plain-text version of the verification email."""
    return (
        "ResearchOS — Email Verification\n"
        "================================\n\n"
        f"Your verification code is: {otp}\n\n"
        "This code expires in 10 minutes.\n\n"
        "If you did not create this account, you can safely ignore this email."
    )

def password_reset_email_body(otp: str) -> str:
    """Return plain-text version of the password reset email."""
    return (
        "ResearchOS — Password Reset\n"
        "===========================\n\n"
        f"Your password reset code is: {otp}\n\n"
        "This code expires in 10 minutes.\n\n"
        "If you did not request a password reset, you can safely ignore this email."
    )
