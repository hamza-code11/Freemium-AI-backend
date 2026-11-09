import smtplib
from email.message import EmailMessage

from app.core.config import (
    SMTP_HOST,
    SMTP_PORT,
    SMTP_USER,
    SMTP_PASSWORD,
    SMTP_FROM_EMAIL
)


class EmailService:

    @staticmethod
    def send_password_reset_otp(email: str, otp: str):
        message = EmailMessage()

        message["Subject"] = "Password Reset OTP - Freemium AI"
        message["From"] = SMTP_FROM_EMAIL
        message["To"] = email

        message.set_content(
            f"""
Hello,

We received a request to reset your Freemium AI account password.

Your 6-digit verification code is:

{otp}

This code will expire in 5 minutes.

If you did not request a password reset, you can safely ignore this email.

Regards,
Freemium AI Team
            """
        )

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(message)
            