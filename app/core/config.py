import os
from dotenv import load_dotenv

load_dotenv()

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is missing in .env file")


# JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
)

if not SECRET_KEY:
    raise ValueError("SECRET_KEY is missing in .env file")

REFRESH_TOKEN_EXPIRE_DAYS = int(
    os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")
)

COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"


# Email Configuration
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL")



GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_CAMPAIGN_API_KEY = os.getenv("GEMINI_CAMPAIGN_API_KEY")
GEMINI_RECOMMENDATION_API_KEY = os.getenv("GEMINI_RECOMMENDATION_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is missing in .env file")
    
if not GEMINI_CAMPAIGN_API_KEY:
    raise ValueError("GEMINI_CAMPAIGN_API_KEY is missing in .env file")


if not GEMINI_RECOMMENDATION_API_KEY:
    raise ValueError("GEMINI_RECOMMENDATION_API_KEY is missing in .env file")

