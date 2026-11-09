import smtplib
from email.message import EmailMessage
import os
from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

print(f"Connecting to {SMTP_HOST}:{SMTP_PORT} as {SMTP_USER}...")

try:
    msg = EmailMessage()
    msg['Subject'] = 'Test OTP Email'
    msg['From'] = SMTP_USER
    msg['To'] = SMTP_USER
    msg.set_content('This is a test email from your FastAPI backend.')

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
        server.set_debuglevel(1) # Poora communication dikhayega
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)
    print("✅ Email sent successfully! Inbox/Spam check karein.")
except Exception as e:
    print(f"❌ Failed: {e}")