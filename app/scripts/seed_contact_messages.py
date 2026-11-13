"""
Seed 1 million fake contact messages into `contact_messages` table.

Usage:
    python seed_contact_messages.py

Options (edit at top of file):
    TOTAL_ROWS  = 1_000_000   # how many records to insert
    BATCH_SIZE  = 5_000       # per-batch inserts (memory-safe)
"""

import os
import sys
import time
import random
from datetime import datetime, timedelta, timezone

# Make sure project imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from faker import Faker
from sqlalchemy import text

from app.core.database import SessionLocal, engine
from app.models.contact_message import ContactMessage


# ------------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------------
TOTAL_ROWS = 1_000_000
BATCH_SIZE = 5_000


SUBJECTS = [
    "Question about pricing",
    "Need help with my account",
    "Feature request",
    "Report a bug",
    "Request a demo",
    "Enterprise inquiry",
    "Partnership proposal",
    "Feedback on product",
    "Billing question",
    "Cancel subscription",
    "API integration help",
    "Data export request",
    "Security concern",
    "General inquiry",
    "Sales question",
    "Technical support",
    "Refund request",
    "Account upgrade",
    "Custom solution needed",
    "Feature doesn't work",
]


MESSAGE_TEMPLATES = [
    "Hi, I wanted to ask about {topic}. My account is {account}. Could you help me with this? Thanks.",
    "Hello team, I'm having trouble with {topic}. Please advise on the next steps.",
    "I'm very interested in your {topic} offering. Could you share more details and pricing?",
    "Quick question about {topic} — is there an enterprise tier available?",
    "I encountered an error while using {topic}. Error code: {code}. Can you look into this?",
    "Loving the product so far! One suggestion: {topic} could be improved. Thanks for the great work.",
    "My {topic} stopped working yesterday. I've been a paying customer for {months} months.",
    "Could you clarify how {topic} integrates with other tools? We use a lot of SaaS apps.",
    "I'd like to request a refund for the last billing cycle. Reason: {topic}.",
    "Hi, I need urgent help with {topic}. This is blocking our production workflow.",
    "I'd love to schedule a demo of your {topic} feature with my team.",
    "Can you tell me if the {topic} feature is available on the free plan?",
    "We're considering your product for our company (size: {size}). Please send pricing.",
    "Please cancel my subscription. {topic} didn't meet my expectations.",
    "Is there a way to export all my data related to {topic}? I need it for backup.",
    "Great product! Just wanted to say {topic} has helped our team a lot.",
    "I think I found a bug in {topic}. Steps to reproduce: open dashboard, click save.",
    "Could you recommend best practices for using {topic} at scale?",
    "My billing invoice for {topic} seems incorrect. Please verify.",
    "We need a custom integration for {topic}. Who should I contact?",
]

TOPIC_POOL = [
    "billing", "subscriptions", "API rate limits", "data export", "user management",
    "the dashboard", "AI generation", "campaign planner", "growth recommendations",
    "reports", "analytics", "multi-language support", "SSO login", "password reset",
    "email notifications", "usage limits", "upgrades", "downgrades",
]

MONTHS_POOL = [1, 2, 3, 6, 9, 12, 18, 24, 36]
SIZE_POOL = ["10", "50", "100", "250", "500", "1000+"]


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _random_created_at(days_back: int = 365) -> datetime:
    """Spread records across last `days_back` days."""
    delta = timedelta(
        seconds=random.randint(0, days_back * 24 * 60 * 60),
    )
    return _now_utc() - delta


def _make_row(fake: Faker) -> dict:
    name = fake.name()
    email = fake.email()

    if random.random() < 0.2:
        email = f"{fake.user_name()}@{fake.free_email_domain()}"

    subject = random.choice(SUBJECTS)
    template = random.choice(MESSAGE_TEMPLATES)
    message = template.format(
        topic=random.choice(TOPIC_POOL),
        account=fake.ean(length=13)[:10],
        code=fake.numerify("#####"),
        months=random.choice(MONTHS_POOL),
        size=random.choice(SIZE_POOL),
    )

    return {
        "name": name[:120],
        "email": email.lower()[:255],
        "subject": subject[:200],
        "message": message,
        "ip_address": fake.ipv4(),
        "user_agent": fake.user_agent()[:500],
        "is_read": 1 if random.random() < 0.35 else 0,
        "created_at": _random_created_at(days_back=365),
    }


def seed():
    fake = Faker()
    Faker.seed(42)
    random.seed(42)

    print(f"[seed] Target   : {TOTAL_ROWS:,} rows")
    print(f"[seed] Batch    : {BATCH_SIZE:,} rows/batch")
    print(f"[seed] Batches  : {TOTAL_ROWS // BATCH_SIZE} (+ remainder)")
    print()

    # Ensure table exists
    ContactMessage.__table__.create(bind=engine, checkfirst=True)

    start_ts = time.time()
    inserted = 0

    db = SessionLocal()
    try:
        while inserted < TOTAL_ROWS:
            current_batch = min(BATCH_SIZE, TOTAL_ROWS - inserted)
            rows = [_make_row(fake) for _ in range(current_batch)]

            db.bulk_insert_mappings(ContactMessage, rows)
            db.commit()

            inserted += current_batch
            pct = inserted / TOTAL_ROWS * 100
            elapsed = time.time() - start_ts
            rate = inserted / elapsed if elapsed > 0 else 0
            eta = (TOTAL_ROWS - inserted) / rate if rate > 0 else 0

            print(
                f"[seed] Inserted {inserted:>9,} / {TOTAL_ROWS:,} "
                f"({pct:5.1f}%)  ·  "
                f"{rate:>7,.0f} rows/sec  ·  "
                f"ETA {int(eta)}s"
            )
    except KeyboardInterrupt:
        print("\n[seed] Interrupted by user. Partial insert kept.")
    except Exception as e:
        db.rollback()
        print(f"\n[seed] ERROR: {e}")
        raise
    finally:
        db.close()

    total_time = time.time() - start_ts
    print()
    print(f"[seed] Done. {inserted:,} rows in {total_time:.1f}s")


def verify():
    db = SessionLocal()
    try:
        total = db.execute(text("SELECT COUNT(*) FROM contact_messages")).scalar()
        unread = db.execute(
            text("SELECT COUNT(*) FROM contact_messages WHERE is_read = 0")
        ).scalar()
        print()
        print(f"[verify] Total  : {total:,}")
        print(f"[verify] Unread : {unread:,}")
        print(f"[verify] Read   : {total - unread:,}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
    verify()