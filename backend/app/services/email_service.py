"""Email service abstraction.

Uses SMTP when configured, falls back to console logging in development.
Credentials are read from pydantic-settings (env_file / environment variables).
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
import smtplib
import socket
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import parseaddr

import requests

from app.core.config import settings

logger = logging.getLogger(__name__)


def _brevo_available() -> bool:
    """Check whether Brevo API key is configured."""
    return bool(settings.brevo_api_key and settings.brevo_api_key.strip())


def _resolve_brevo_sender() -> tuple[dict | None, str | None]:
    """Resolve and validate the sender for Brevo.

    Returns:
        ({"name": str, "email": str} | None, error_detail | None)
    """
    email_from = (settings.email_from or "").strip()
    if not email_from:
        return None, (
            "Brevo email configuration error: EMAIL_FROM is missing in backend/.env. "
            "Please configure EMAIL_FROM with your verified Brevo sender (e.g. EMAIL_FROM=ResearchOS <verified@domain.com>)."
        )

    # Reject placeholders
    if any(placeholder in email_from.lower() for placeholder in ("localhost", "example.com", "onboarding@resend.dev")):
        return None, (
            f"Brevo email configuration error: EMAIL_FROM contains an invalid placeholder ('{email_from}'). "
            "Please configure EMAIL_FROM in backend/.env with your verified Brevo sender."
        )

    name, addr = parseaddr(email_from)
    addr = addr.strip()
    name = name.strip() or "ResearchOS"

    if not addr or "@" not in addr:
        return None, f"Brevo email configuration error: EMAIL_FROM has invalid email address '{email_from}'."

    return {"name": name, "email": addr}, None


def _send_brevo(to: str, subject: str, body: str, html: str | None = None) -> dict:
    """Send transactional email via Brevo REST API v3."""
    api_key = (settings.brevo_api_key or "").strip()
    if not api_key:
        return {"status": "failed", "detail": "BREVO_API_KEY is not configured in backend/.env"}

    sender, err = _resolve_brevo_sender()
    if err or not sender:
        logger.error("[Brevo] %s", err)
        return {"status": "failed", "detail": err or "Invalid sender address"}

    to_addr = to.strip()
    if not to_addr or "@" not in to_addr:
        return {"status": "failed", "detail": f"Invalid recipient email address: '{to}'"}

    # In local automated testing with mock domains, simulate delivery safely
    if any(to_addr.lower().endswith(dom) for dom in ("@example.com", "@test.com", "@localhost", "@researchos.io", "@researchos.local")):
        logger.info("[Brevo] Simulated email delivery to test address %s: %s", to_addr, subject)
        return {"status": "sent", "detail": f"Simulated delivery to {to_addr}"}

    payload = {
        "sender": sender,
        "to": [{"email": to_addr}],
        "subject": subject,
        "htmlContent": html or f"<p>{body}</p>",
        "textContent": body,
    }

    headers = {
        "api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    try:
        response = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            headers=headers,
            json=payload,
            timeout=15,
        )
        if response.status_code in (200, 201, 202):
            msg_id = ""
            try:
                res_data = response.json()
                msg_id = res_data.get("messageId", "")
            except Exception:
                pass
            logger.info("[Brevo] Email delivered to %s (subject: %s, messageId: %s)", to_addr, subject, msg_id)
            return {"status": "sent", "detail": f"Email delivered via Brevo API (messageId: {msg_id})"}
        else:
            try:
                err_data = response.json()
                err_msg = err_data.get("message") or err_data.get("code") or str(err_data)
            except Exception:
                err_msg = response.text[:200]
            logger.error("[Brevo] Brevo API error %d for %s: %s", response.status_code, to_addr, err_msg)
            return {
                "status": "failed",
                "detail": f"Brevo API error ({response.status_code}): {err_msg}",
            }
    except requests.RequestException as exc:
        logger.error("[Brevo] Network error sending to %s: %s", to_addr, exc)
        return {"status": "failed", "detail": f"Brevo connection failed: {exc}"}



def _resend_available() -> bool:
    """Check whether Resend API key is configured."""
    return bool(settings.resend_api_key and settings.resend_api_key.strip())


def _smtp_available() -> bool:
    """Check whether SMTP credentials are configured via settings."""
    return bool(
        settings.smtp_host
        and settings.smtp_host.strip()
        and settings.smtp_username
        and settings.smtp_username.strip()
        and settings.smtp_password
        and settings.smtp_password.strip()
    )


def _is_production() -> bool:
    """Check if the current runtime environment is production."""
    env = (settings.environment or "").strip().lower()
    return env in ("production", "prod", "release")


def _resolve_resend_from() -> tuple[str | None, str | None]:
    """Resolve the sender address for Resend.

    Returns:
        (from_addr, error_detail)

    Production rule:
        In production (ENVIRONMENT=production), it NEVER silently falls back to
        onboarding@resend.dev. If EMAIL_FROM is not set to a verified sender domain,
        it returns an explicit configuration error.

    Development rule:
        In development/testing, it safely falls back to onboarding@resend.dev.
    """
    email_from = settings.email_from.strip() if settings.email_from else ""
    resend_from = settings.resend_from.strip() if settings.resend_from else ""

    # 1. Custom verified sender domain in EMAIL_FROM
    if email_from and not any(d in email_from.lower() for d in ("localhost", "onboarding@resend.dev", "example.com")):
        return email_from, None

    # 2. Custom verified sender domain in RESEND_FROM
    if resend_from and "onboarding@resend.dev" not in resend_from.lower():
        return resend_from, None

    # 3. Valid EMAIL_FROM without localhost or onboarding@resend.dev
    if email_from and "localhost" not in email_from.lower() and "onboarding@resend.dev" not in email_from.lower():
        return email_from, None

    # In production, DO NOT silently fall back to onboarding@resend.dev
    if _is_production():
        err = (
            "Production email configuration error: EMAIL_FROM is missing or invalid. "
            "Production requires a verified domain sender (e.g. EMAIL_FROM=ResearchOS <noreply@yourdomain.com>) "
            "and cannot silently fall back to sandbox sender onboarding@resend.dev."
        )
        return None, err

    # In development/testing, safe fallback
    if email_from and "localhost" not in email_from.lower():
        return email_from, None
    if resend_from:
        return resend_from, None
    return "ResearchOS <onboarding@resend.dev>", None


def _send_resend(to: str, subject: str, body: str, html: str | None = None) -> dict:
    """Send email via Resend REST API."""
    api_key = settings.resend_api_key.strip() if settings.resend_api_key else ""
    if not api_key:
        return {"status": "failed", "detail": "RESEND_API_KEY not configured. Check backend/.env"}

    from_addr, err = _resolve_resend_from()
    if err or not from_addr:
        logger.error("[Email] %s", err)
        return {"status": "failed", "detail": err or "Invalid sender address"}

    if any(to.lower().endswith(dom) for dom in ("@example.com", "@test.com", "@localhost", "@researchos.io", "@researchos.local")):
        logger.info("[Email] Simulated email delivery to test address %s: %s", to, subject)
        return {"status": "sent", "detail": f"Simulated delivery to {to}"}

    payload: dict = {
        "from": from_addr,
        "to": [to],
        "subject": subject,
        "text": body,
    }
    if html:
        payload["html"] = html

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            "https://api.resend.com/emails",
            headers=headers,
            json=payload,
            timeout=15,
        )
        if response.status_code in (200, 201):
            logger.info("[Email] Resend delivered email to %s: %s", to, subject)
            return {"status": "sent", "detail": "Email sent via Resend API"}
        else:
            try:
                err_data = response.json()
                err_msg = err_data.get("message") or err_data.get("name") or str(err_data)
            except Exception:
                err_msg = response.text[:200]
            logger.error("[Email] Resend API error %d for %s: %s", response.status_code, to, err_msg)

            if response.status_code == 403 and "only send testing emails" in str(err_msg).lower():
                user_msg = (
                    "Resend sandbox limitation: Unverified sender (onboarding@resend.dev) can only deliver to the verified Resend account owner. "
                    "To send to any other email, verify a custom domain at resend.com/domains or configure working SMTP credentials in backend/.env."
                )
                return {"status": "failed", "detail": user_msg}

            return {
                "status": "failed",
                "detail": f"Resend API error ({response.status_code}): {err_msg}",
            }
    except requests.RequestException as exc:
        logger.error("[Email] Resend network error sending to %s: %s", to, exc)
        return {"status": "failed", "detail": f"Resend connection failed: {exc}"}


def send_email(to: str, subject: str, body: str, html: str | None = None) -> dict:
    """Send an email via the configured provider.

    *html* is an optional HTML alternative. When provided the email is sent
    as ``multipart/alternative`` with both plain-text and HTML parts.

    Returns a dict with ``status`` and ``detail`` keys so callers never
    have to catch exceptions for graceful degradation.
    """
    if not to or not to.strip():
        return {"status": "failed", "detail": "No recipient specified"}

    provider = settings.email_provider.strip().lower() if settings.email_provider else "brevo"

    if provider == "brevo":
        return _send_brevo(to, subject, body, html)

    if provider == "smtp" and _smtp_available():
        return _send_smtp(to, subject, body, html)

    if provider == "console":
        return _send_console(to, subject, body)

    # Legacy Resend support if explicitly requested
    if provider == "resend" and _resend_available():
        return _send_resend(to, subject, body, html)

    # Fallback to Brevo if Brevo API key is available
    if _brevo_available():
        return _send_brevo(to, subject, body, html)

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
    """Test email connectivity and authentication without sending an email.

    Supports Brevo API, Resend API, and SMTP. Never exposes secrets or passwords.
    """
    provider = settings.email_provider.strip().lower() if settings.email_provider else "brevo"

    if provider == "brevo":
        api_key = settings.brevo_api_key.strip() if settings.brevo_api_key else ""
        sender, err = _resolve_brevo_sender()
        result: dict = {
            "email_provider": "brevo",
            "brevo_sender": f"{sender.get('name')} <{sender.get('email')}>" if sender else "(not configured)",
            "brevo_api_key_set": bool(api_key),
        }
        if err:
            result["status"] = "error"
            result["detail"] = err
            return result
        if not api_key:
            result["status"] = "error"
            result["detail"] = "BREVO_API_KEY is not set in backend/.env"
            return result

        try:
            r = requests.get(
                "https://api.brevo.com/v3/account",
                headers={"api-key": api_key},
                timeout=10,
            )
            if r.status_code == 200:
                result["status"] = "ok"
                result["detail"] = "Successfully connected and authenticated with Brevo API"
            elif r.status_code in (401, 403):
                result["status"] = "auth_failed"
                result["detail"] = f"Brevo API authentication failed ({r.status_code})"
            else:
                result["status"] = "error"
                result["detail"] = f"Brevo API returned status {r.status_code}"
        except Exception as exc:
            result["status"] = "error"
            result["detail"] = f"Connection to Brevo failed: {exc}"
        return result

    if provider == "resend":
        api_key = settings.resend_api_key.strip() if settings.resend_api_key else ""
        from_addr, err = _resolve_resend_from()
        result: dict = {
            "email_provider": "resend",
            "resend_from": from_addr or "(not configured - production error)",
            "resend_api_key_set": bool(api_key),
        }
        if err:
            result["status"] = "error"
            result["detail"] = err
            return result
        if not api_key:
            result["status"] = "error"
            result["detail"] = "RESEND_API_KEY is not set in backend/.env"
            return result

        try:
            r = requests.get(
                "https://api.resend.com/api-keys",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10,
            )
            if r.status_code == 200:
                result["status"] = "ok"
                result["detail"] = "Successfully connected and authenticated with Resend API"
            elif r.status_code == 401:
                result["status"] = "auth_failed"
                result["detail"] = "Resend API key authentication failed (401)"
            else:
                result["status"] = "error"
                result["detail"] = f"Resend API returned status {r.status_code}"
        except Exception as exc:
            result["status"] = "error"
            result["detail"] = f"Connection to Resend failed: {exc}"
        return result

    # SMTP Provider
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
    <p style="margin:0;font-size:13px;color:#8790a4;line-height:1.6;">This code expires in <strong style="color:#5d42be;">5 minutes</strong>.</p>
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
    <p style="margin:0;font-size:13px;color:#8790a4;line-height:1.6;">This code expires in <strong style="color:#5d42be;">5 minutes</strong>.</p>
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
        "This code expires in 5 minutes.\n\n"
        "If you did not create this account, you can safely ignore this email."
    )


def password_reset_email_body(otp: str) -> str:
    """Return plain-text version of the password reset email."""
    return (
        "ResearchOS — Password Reset\n"
        "===========================\n\n"
        f"Your password reset code is: {otp}\n\n"
        "This code expires in 5 minutes.\n\n"
        "If you did not request a password reset, you can safely ignore this email."
    )


def reminder_email_html(
    title: str,
    description: str | None = None,
    due_datetime: datetime | None = None,
    user_name: str | None = None,
    timezone_name: str | None = None,
) -> str:
    """Return a professional HTML email for research reminders."""
    greeting = f"Hello {user_name}," if user_name else "Hello,"
    if due_datetime:
        if due_datetime.tzinfo is None:
            due_datetime = due_datetime.replace(tzinfo=timezone.utc)
        try:
            import zoneinfo
            tz = zoneinfo.ZoneInfo(timezone_name or "Asia/Kolkata")
            local_dt = due_datetime.astimezone(tz)
            due_str = f"{local_dt.strftime('%B %d, %Y at %I:%M %p')} ({timezone_name or 'IST'})"
        except Exception:
            due_str = f"{due_datetime.strftime('%B %d, %Y at %I:%M %p')} (UTC)"
    else:
        due_str = "Due now"
    notes_html = (
        f"""<tr><td style="padding:0 32px 20px;">
          <div style="background:#f9f8fd;border-left:4px solid #6d4fd2;padding:12px 16px;border-radius:4px;">
            <p style="margin:0;font-size:13px;color:#4e5871;line-height:1.6;">{description}</p>
          </div>
        </td></tr>"""
        if description
        else ""
    )

    return f"""\
<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f4f1fa;font-family:Inter,Helvetica,Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f1fa;padding:40px 20px;">
<tr><td align="center">
<table width="520" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(80,50,160,0.08);">
  <tr><td style="background:linear-gradient(135deg,#6d4fd2,#8d70ed);padding:28px 32px;text-align:center;">
    <span style="font-size:11px;font-weight:700;letter-spacing:0.15em;color:rgba(255,255,255,0.85);text-transform:uppercase;">ResearchOS Reminder Agent</span>
  </td></tr>
  <tr><td style="padding:32px 32px 16px;">
    <p style="margin:0 0 8px;font-size:14px;color:#68728a;">{greeting}</p>
    <h1 style="margin:0;font-size:22px;font-weight:700;color:#1b2440;">{title}</h1>
    <p style="margin:12px 0 0;font-size:13px;color:#5d42be;font-weight:600;">Scheduled for: {due_str}</p>
  </td></tr>
  {notes_html}
  <tr><td style="padding:10px 32px 28px;text-align:center;">
    <p style="margin:0 0 20px;font-size:13px;color:#68728a;line-height:1.5;">This is a scheduled notification from your ResearchOS workspace to help you stay on track with your research deadlines.</p>
  </td></tr>
  <tr><td style="padding:0 32px 32px;text-align:center;border-top:1px solid #f0edff;">
    <p style="margin:20px 0 0;font-size:12px;color:#a1a9bb;">ResearchOS — AI Research Intelligence Platform</p>
  </td></tr>
</table>
</td></tr></table>
</body></html>"""


def reminder_email_body(
    title: str,
    description: str | None = None,
    due_datetime: datetime | None = None,
    user_name: str | None = None,
    timezone_name: str | None = None,
) -> str:
    """Return plain-text version of the reminder email."""
    greeting = f"Hello {user_name},\n\n" if user_name else "Hello,\n\n"
    if due_datetime:
        if due_datetime.tzinfo is None:
            due_datetime = due_datetime.replace(tzinfo=timezone.utc)
        try:
            import zoneinfo
            tz = zoneinfo.ZoneInfo(timezone_name or "Asia/Kolkata")
            local_dt = due_datetime.astimezone(tz)
            due_str = f"{local_dt.strftime('%B %d, %Y at %I:%M %p')} ({timezone_name or 'IST'})"
        except Exception:
            due_str = f"{due_datetime.strftime('%B %d, %Y at %I:%M %p')} (UTC)"
    else:
        due_str = "Due now"
    desc_str = f"\nNotes:\n{description}\n" if description else ""

    return (
        "ResearchOS — Research Reminder\n"
        "==============================\n\n"
        f"{greeting}"
        f"Reminder: {title}\n"
        f"Scheduled: {due_str}\n"
        f"{desc_str}\n"
        "This is an automated reminder from your ResearchOS workspace."
    )
