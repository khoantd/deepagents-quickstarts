"""Email service for sending verification and password reset emails."""

from __future__ import annotations

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from .settings import get_settings

settings = get_settings()


async def send_email(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str | None = None,
) -> None:
    """Send an email using SMTP.

    Args:
        to_email: Recipient email address
        subject: Email subject
        html_body: HTML email body
        text_body: Plain text email body (optional)

    Raises:
        ValueError: If SMTP is not configured
    """
    if not settings.smtp_host or not settings.smtp_user or not settings.smtp_password:
        # In development, just log instead of raising
        print(f"[Email] Would send to {to_email}: {subject}")
        print(f"[Email] Body: {html_body}")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from_email or settings.smtp_user
    msg["To"] = to_email

    if text_body:
        msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            if settings.smtp_use_tls:
                server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
    except Exception as e:
        raise ValueError(f"Failed to send email: {e}") from e


async def send_email_verification(
    email: str,
    name: str,
    token: str,
) -> None:
    """Send email verification email.

    Args:
        email: Recipient email address
        name: User name
        token: Verification token
    """
    frontend_url = settings.frontend_url
    verification_url = f"{frontend_url}/verify-email?token={token}"

    subject = "Verify your email address"
    html_body = f"""
    <html>
      <body>
        <h2>Verify your email address</h2>
        <p>Hi {name},</p>
        <p>Thank you for signing up! Please verify your email address by clicking the link below:</p>
        <p><a href="{verification_url}">Verify Email</a></p>
        <p>Or copy and paste this link into your browser:</p>
        <p>{verification_url}</p>
        <p>This link will expire in 24 hours.</p>
        <p>If you didn't create an account, you can safely ignore this email.</p>
      </body>
    </html>
    """
    text_body = f"""
    Hi {name},

    Thank you for signing up! Please verify your email address by visiting this link:

    {verification_url}

    This link will expire in 24 hours.

    If you didn't create an account, you can safely ignore this email.
    """

    await send_email(email, subject, html_body, text_body)


async def send_password_reset(
    email: str,
    name: str,
    token: str,
) -> None:
    """Send password reset email.

    Args:
        email: Recipient email address
        name: User name
        token: Password reset token
    """
    frontend_url = settings.frontend_url
    reset_url = f"{frontend_url}/reset-password?token={token}"

    subject = "Reset your password"
    html_body = f"""
    <html>
      <body>
        <h2>Reset your password</h2>
        <p>Hi {name},</p>
        <p>You requested to reset your password. Click the link below to reset it:</p>
        <p><a href="{reset_url}">Reset Password</a></p>
        <p>Or copy and paste this link into your browser:</p>
        <p>{reset_url}</p>
        <p>This link will expire in 1 hour.</p>
        <p>If you didn't request a password reset, you can safely ignore this email.</p>
      </body>
    </html>
    """
    text_body = f"""
    Hi {name},

    You requested to reset your password. Visit this link to reset it:

    {reset_url}

    This link will expire in 1 hour.

    If you didn't request a password reset, you can safely ignore this email.
    """

    await send_email(email, subject, html_body, text_body)

