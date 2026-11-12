# app/services/admin_stats_service.py

from datetime import datetime, timedelta, timezone
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.user_session import UserSession
from app.models.content_generation import ContentGeneration
from app.models.campaign import Campaign
from app.models.growth_recommendation import GrowthRecommendation
from app.schemas.admin_stats import AdminUserStats


class AdminStatsService:

    @staticmethod
    def get_user_stats(db: Session) -> AdminUserStats:
        """
        FAST stats — 3-4 total queries.
        - Total users (role='user')
        - Suspended users
        - Active users (last 30 days, EXCLUDING suspended)
        - Inactive users
        """
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)

        #  1. Total users (only role='user')
        total_users = (
            db.query(func.count(User.id))
            .filter(User.role == "user")
            .scalar()
        ) or 0

        #  2. Suspended users (only role='user')
        suspended_users = (
            db.query(func.count(User.id))
            .filter(
                User.role == "user",
                User.is_suspended == True,
            )
            .scalar()
        ) or 0

        #  3. Active users (last 30 days) — raw count
        content_subq = (
            db.query(ContentGeneration.user_id)
            .filter(ContentGeneration.created_at >= thirty_days_ago)
            .subquery()
        )
        campaign_subq = (
            db.query(Campaign.user_id)
            .filter(Campaign.created_at >= thirty_days_ago)
            .subquery()
        )
        rec_subq = (
            db.query(GrowthRecommendation.user_id)
            .filter(GrowthRecommendation.created_at >= thirty_days_ago)
            .subquery()
        )
        session_subq = (
            db.query(UserSession.user_id)
            .filter(UserSession.created_at >= thirty_days_ago)
            .subquery()
        )

        # Single query — count distinct active users
        # ✅ is_suspended=False filter → suspended never counted as active
        active_users = (
            db.query(func.count(func.distinct(User.id)))
            .filter(
                User.role == "user",
                User.is_suspended.is_(False),   #  FIX — suspended excluded
                or_(
                    User.id.in_(content_subq),
                    User.id.in_(campaign_subq),
                    User.id.in_(rec_subq),
                    User.id.in_(session_subq),
                ),
            )
            .scalar()
        ) or 0

        #  4. Inactive users
        inactive_users = max(0, total_users - active_users - suspended_users)

        return AdminUserStats(
            total_users=total_users,
            active_users=active_users,
            inactive_users=inactive_users,
            suspended_users=suspended_users,
        )


    