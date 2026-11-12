# app/scripts/seed_users.py

"""
Seed script for creating 10,000 dummy users + sample data.
Usage:
    python -m app.scripts.seed_users

⚠️ WARNING: Ye script ~70,000 records create karega.
   Database me 5-15 minutes lag sakte hain.
"""

from datetime import datetime, timedelta, timezone
from faker import Faker
from sqlalchemy.orm import Session
from uuid import uuid4
import secrets
import hashlib
import random
import sys

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User
from app.models.business_profile import BusinessProfile
from app.models.content_generation import ContentGeneration
from app.models.campaign import Campaign
from app.models.growth_recommendation import GrowthRecommendation
from app.models.user_session import UserSession

fake = Faker()

# ============================================
# CONFIG — 10,000 USERS
# ============================================
NUM_USERS = 10000
BATCH_SIZE = 500                # Insert in batches (fast)
SUSPENDED_COUNT = 100           # First 100 suspended

# Data generation limits (performance ke liye)
CONTENT_PER_USER = 2
CAMPAIGN_PER_USER = 1
RECOMMENDATION_PER_USER = 1
SESSIONS_PER_USER = 2

PASSWORD = "12345678"           # Sabka same password

BUSINESS_TYPES = [
    'E-commerce', 'Retail', 'Technology', 'Software / SaaS', 'Digital Agency',
    'Education', 'Healthcare', 'Food & Restaurant', 'Consulting', 'Freelancing',
]

TARGET_AUDIENCES = [
    "young_adults_men", "young_adults_women", "middle_age_men",
    "middle_age_women", "teenagers_men", "teenagers_women",
]

PLATFORMS = ["instagram", "facebook", "youtube", "tiktok", "linkedin", "twitter", "website"]
CONTENT_TYPES = ["video", "adcopy", "product"]
TONES = ["Creative", "Professional", "Friendly", "Urgent", "Luxury"]
LANGUAGES = ["English", "Urdu", "Roman Urdu", "Hindi", "Arabic"]

OBJECTIVES = ["awareness", "leads", "sales", "launch", "engagement"]
CHANNELS = ["instagram", "facebook", "linkedin", "youtube", "twitter", "email", "website"]

FIRST_NAMES = [
    "Ahmed", "Sara", "Usman", "Ayesha", "Bilal", "Fatima", "Hassan", "Zara",
    "Ali", "Noor", "Hamza", "Mariam", "Faizan", "Rabia", "Kashif", "Sana",
    "Imran", "Hina", "Faisal", "Areeba", "Adnan", "Iqra", "Tariq", "Nida",
]

LAST_NAMES = [
    "Khan", "Ali", "Malik", "Sheikh", "Ahmed", "Raza", "Iqbal", "Hassan",
    "Hussain", "Siddiqui", "Qureshi", "Butt", "Chaudhry", "Shah", "Mirza",
]


# ============================================
# HELPERS
# ============================================
def hash_refresh(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def generate_unique_email(index: int, used_emails: set) -> str:
    """Generate unique email with index to avoid duplicates."""
    while True:
        first = random.choice(FIRST_NAMES).lower()
        last = random.choice(LAST_NAMES).lower()
        rand = random.randint(1000, 999999)
        email = f"{first}.{last}{rand}.{index}@example.com"

        if email not in used_emails:
            used_emails.add(email)
            return email


def build_user_batch(start_idx: int, count: int, hashed_password: str, used_emails: set) -> list[User]:
    """Build a batch of user objects."""
    users = []
    for i in range(count):
        idx = start_idx + i
        name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        email = generate_unique_email(idx, used_emails)
        is_suspended = idx < SUSPENDED_COUNT

        user = User(
            name=name,
            email=email,
            password=hashed_password,
            role="user",
            is_suspended=is_suspended,
            created_at=datetime.now(timezone.utc) - timedelta(days=random.randint(0, 90)),
        )
        users.append(user)
    return users


# ============================================
# MAIN SEED
# ============================================
def seed():
    db: Session = SessionLocal()

    try:
        print(f"🌱 Seeding {NUM_USERS} users...")
        print(f"   Password for all: {PASSWORD}")
        print(f"   Batch size: {BATCH_SIZE}\n")

        # Pre-hash password ONCE (bahot fast)
        hashed_password = hash_password(PASSWORD)

        used_emails = set()
        total_batches = (NUM_USERS + BATCH_SIZE - 1) // BATCH_SIZE
        start_time = datetime.now()

        for batch_num in range(total_batches):
            batch_start = batch_num * BATCH_SIZE
            batch_count = min(BATCH_SIZE, NUM_USERS - batch_start)

            # ----- 1. BUILD + INSERT USERS BATCH -----
            users = build_user_batch(batch_start, batch_count, hashed_password, used_emails)
            db.add_all(users)
            db.flush()  # Get user IDs

            # ----- 2. BUILD RELATED DATA -----
            sessions = []
            businesses = []
            contents = []
            campaigns = []
            recommendations = []

            for user in users:
                # Business Profile
                business = BusinessProfile(
                    user_id=user.id,
                    business_name=fake.company(),
                    business_type=random.choice(BUSINESS_TYPES),
                    services=fake.text(max_nb_chars=200),
                    target_audience=random.sample(TARGET_AUDIENCES, k=random.randint(1, 3)),
                    business_goals=fake.sentence(nb_words=12),
                    business_description=fake.text(max_nb_chars=300),
                )
                businesses.append(business)

                # Sessions (login activity)
                for _ in range(SESSIONS_PER_USER):
                    session_id = str(uuid4())
                    secret = secrets.token_urlsafe(48)
                    token_hash = hash_refresh(secret)
                    created_at = datetime.now(timezone.utc) - timedelta(days=random.randint(0, 30))
                    expires_at = created_at + timedelta(days=7)

                    sessions.append(UserSession(
                        id=session_id,
                        user_id=user.id,
                        refresh_token_hash=token_hash,
                        expires_at=expires_at,
                        created_at=created_at,
                    ))

                # Content Generations
                for _ in range(CONTENT_PER_USER):
                    days_ago = random.randint(0, 30)
                    contents.append(ContentGeneration(
                        user_id=user.id,
                        platform=random.choice(PLATFORMS),
                        content_type=random.choice(CONTENT_TYPES),
                        topic=fake.sentence(nb_words=5),
                        target_audience=random.sample(TARGET_AUDIENCES, k=random.randint(1, 2)),
                        tone=random.choice(TONES),
                        language=random.choice(LANGUAGES),
                        notes=None,
                        generated_content=fake.paragraph(nb_sentences=5),
                        created_at=datetime.now(timezone.utc) - timedelta(days=days_ago),
                    ))

                # Campaigns
                for _ in range(CAMPAIGN_PER_USER):
                    days_ago = random.randint(0, 30)
                    campaigns.append(Campaign(
                        user_id=user.id,
                        business_id=business.id,  # Will be linked after flush
                        campaign_name=fake.catch_phrase(),
                        objective=random.choice(OBJECTIVES),
                        product_service=fake.text(max_nb_chars=100),
                        target_audience=random.sample(TARGET_AUDIENCES, k=random.randint(1, 2)),
                        channels=random.sample(CHANNELS, k=random.randint(1, 3)),
                        budget=random.randint(500, 10000),
                        currency="USD",
                        start_date=datetime.now(timezone.utc),
                        end_date=datetime.now(timezone.utc) + timedelta(days=30),
                        tone=random.choice(TONES),
                        notes=None,
                        generated_plan={
                            "title": fake.catch_phrase(),
                            "description": fake.sentence(nb_words=12),
                            "strategy": fake.paragraph(nb_sentences=3),
                            "channels": [{"id": "instagram", "label": "Instagram"}],
                            "weeks": [{"title": "Week 1", "items": ["Setup"]}],
                            "ideas": ["Idea 1", "Idea 2"],
                            "kpis": ["KPI 1", "KPI 2"],
                            "budget": [{"label": "Ads", "pct": 60}, {"label": "Content", "pct": 40}],
                            "total": "$5000",
                        },
                        created_at=datetime.now(timezone.utc) - timedelta(days=days_ago),
                    ))

                # Recommendations
                for _ in range(RECOMMENDATION_PER_USER):
                    days_ago = random.randint(0, 30)
                    recommendations.append(GrowthRecommendation(
                        user_id=user.id,
                        business_id=business.id,
                        business_goals=fake.sentence(nb_words=10),
                        challenges=fake.sentence(nb_words=8),
                        target_audience=random.sample(TARGET_AUDIENCES, k=2),
                        ai_instruction=None,
                        recommendations=[{
                            "title": fake.catch_phrase(),
                            "desc": fake.sentence(nb_words=10),
                            "bullets": [fake.sentence(nb_words=6) for _ in range(3)],
                            "benefit": fake.sentence(nb_words=8),
                            "why": fake.sentence(nb_words=10),
                            "checklist": [fake.sentence(nb_words=5) for _ in range(3)],
                            "tools": random.sample(["instagram", "facebook", "canva", "mailchimp"], k=2),
                            "metrics": ["KPI 1", "KPI 2"],
                        }],
                        created_at=datetime.now(timezone.utc) - timedelta(days=days_ago),
                    ))

            # ----- 3. INSERT ALL RELATED DATA -----
            db.add_all(businesses)
            db.flush()  # Get business IDs (needed for campaigns/recs)

            # Update campaigns/recs with correct business_id
            for c in campaigns:
                c.business_id = businesses[0].id if not c.business_id else c.business_id
            for r in recommendations:
                r.business_id = businesses[0].id if not r.business_id else r.business_id

            db.add_all(sessions)
            db.add_all(contents)
            db.add_all(campaigns)
            db.add_all(recommendations)

            # Commit batch
            db.commit()

            # Progress log
            elapsed = (datetime.now() - start_time).total_seconds()
            percent = ((batch_num + 1) / total_batches) * 100
            print(f"  ✅ Batch {batch_num + 1}/{total_batches} ({percent:.1f}%) — {elapsed:.0f}s elapsed")

        # Final summary
        total_time = (datetime.now() - start_time).total_seconds()
        print("\n" + "=" * 50)
        print(f"🎉 SEEDING COMPLETE!")
        print(f"   Total Users: {NUM_USERS}")
        print(f"   Total Time: {total_time:.1f} seconds")
        print(f"   Password: {PASSWORD}")
        print("=" * 50)

    except Exception as e:
        db.rollback()
        print(f"\n❌ Seeding failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    seed()