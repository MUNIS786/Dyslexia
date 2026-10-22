"""
backend/services/email_service.py — Production-grade email dispatch service.
Supports console, mock, and SMTP providers with safe fallbacks and testability.
"""
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional
from core.config import settings

logger = logging.getLogger("dyslexaid.email")

# In-memory test/dev mailbox to inspect dispatched emails in automated tests
_dispatched_emails: List[Dict[str, str]] = []


def get_dispatched_emails() -> List[Dict[str, str]]:
    """Returns a copy of all emails recorded by console/mock provider."""
    return list(_dispatched_emails)


def clear_dispatched_emails() -> None:
    """Clears recorded emails (used in test fixtures)."""
    _dispatched_emails.clear()


class EmailService:
    @staticmethod
    def _build_reset_link(token: str) -> str:
        base = settings.FRONTEND_URL.rstrip("/")
        return f"{base}/reset-password?token={token}"

    @staticmethod
    def _build_verify_link(token: str) -> str:
        base = settings.FRONTEND_URL.rstrip("/")
        return f"{base}/verify-email?token={token}"

    @classmethod
    def send_password_reset_email(cls, to_email: str, token: str) -> bool:
        """Sends password reset link to user."""
        reset_link = cls._build_reset_link(token)
        subject = "DyslexAid — Password Reset Request"
        text_body = (
            f"Hello,\n\n"
            f"A password reset was requested for your DyslexAid account ({to_email}).\n"
            f"Please visit the following link within 1 hour to reset your password:\n\n"
            f"{reset_link}\n\n"
            f"If you did not request this, you can safely ignore this message. Your password will remain unchanged.\n\n"
            f"— The DyslexAid Team"
        )
        html_body = (
            f"<div style='font-family: sans-serif; max-width: 560px; margin: 0 auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;'>"
            f"<h2 style='color: #4f46e5; margin-top: 0;'>DyslexAid Password Reset</h2>"
            f"<p>Hello,</p>"
            f"<p>A password reset was requested for your DyslexAid account (<strong>{to_email}</strong>).</p>"
            f"<p style='margin: 24px 0;'><a href='{reset_link}' style='background-color: #4f46e5; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold;'>Reset My Password</a></p>"
            f"<p style='font-size: 13px; color: #64748b;'>Or copy and paste this link into your browser:<br/><a href='{reset_link}' style='color: #4f46e5;'>{reset_link}</a></p>"
            f"<p style='font-size: 13px; color: #64748b;'>This link will expire in 1 hour. If you did not request a password reset, please ignore this email.</p>"
            f"<hr style='border: none; border-top: 1px solid #e2e8f0; margin: 20px 0;' />"
            f"<p style='font-size: 12px; color: #94a3b8;'>DyslexAid V2 — Universal Accessible Reading Platform</p>"
            f"</div>"
        )
        return cls._dispatch(to_email, subject, text_body, html_body, link=reset_link, category="password_reset")

    @classmethod
    def send_verification_email(cls, to_email: str, token: str) -> bool:
        """Sends email verification link to user."""
        verify_link = cls._build_verify_link(token)
        subject = "DyslexAid — Verify Your Email Address"
        text_body = (
            f"Welcome to DyslexAid!\n\n"
            f"Please confirm your email address by visiting the following link:\n\n"
            f"{verify_link}\n\n"
            f"This link will expire in 24 hours.\n\n"
            f"— The DyslexAid Team"
        )
        html_body = (
            f"<div style='font-family: sans-serif; max-width: 560px; margin: 0 auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;'>"
            f"<h2 style='color: #4f46e5; margin-top: 0;'>Welcome to DyslexAid!</h2>"
            f"<p>Thank you for creating an account with DyslexAid. Please verify your email address to complete your setup:</p>"
            f"<p style='margin: 24px 0;'><a href='{verify_link}' style='background-color: #4f46e5; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold;'>Verify Email Address</a></p>"
            f"<p style='font-size: 13px; color: #64748b;'>Or copy and paste this link into your browser:<br/><a href='{verify_link}' style='color: #4f46e5;'>{verify_link}</a></p>"
            f"<p style='font-size: 13px; color: #64748b;'>This link is valid for 24 hours.</p>"
            f"<hr style='border: none; border-top: 1px solid #e2e8f0; margin: 20px 0;' />"
            f"<p style='font-size: 12px; color: #94a3b8;'>DyslexAid V2 — Universal Accessible Reading Platform</p>"
            f"</div>"
        )
        return cls._dispatch(to_email, subject, text_body, html_body, link=verify_link, category="email_verification")

    @classmethod
    def _dispatch(cls, to_email: str, subject: str, text_body: str, html_body: str, link: str, category: str) -> bool:
        provider = settings.EMAIL_PROVIDER.lower()

        # Always record in memory for test inspectability and audit
        _dispatched_emails.append({
            "to": to_email,
            "subject": subject,
            "link": link,
            "category": category,
            "text": text_body,
        })

        if provider in ("console", "mock", "test"):
            logger.info("[EMAIL DISPATCH - %s] To: %s | Subject: %s | Link: %s", provider.upper(), to_email, subject, link)
            return True

        if provider == "smtp":
            if not settings.SMTP_HOST:
                logger.warning("SMTP requested but SMTP_HOST is not configured. Falling back to console dispatch.")
                return True
            try:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = settings.EMAIL_FROM
                msg["To"] = to_email
                msg.attach(MIMEText(text_body, "plain"))
                msg.attach(MIMEText(html_body, "html"))

                with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
                    server.ehlo()
                    try:
                        server.starttls()
                        server.ehlo()
                    except Exception:
                        pass
                    if settings.SMTP_USER and settings.SMTP_PASSWORD:
                        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                    server.sendmail(settings.EMAIL_FROM, [to_email], msg.as_string())
                logger.info("Successfully dispatched %s email to %s via SMTP", category, to_email)
                return True
            except Exception as e:
                logger.error("Failed to send %s email via SMTP to %s: %s", category, to_email, str(e))
                return False

        logger.info("Unknown EMAIL_PROVIDER '%s'. Email recorded in memory.", provider)
        return True
