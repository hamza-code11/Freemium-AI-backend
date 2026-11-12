# app/services/admin_dashboard_service.py

from datetime import datetime, timedelta, timezone
from typing import Iterable

from sqlalchemy import desc, func, union_all, literal_column
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.user_session import UserSession
from app.models.content_generation import ContentGeneration
from app.models.campaign import Campaign
from app.models.growth_recommendation import GrowthRecommendation
from app.schemas.admin_dashboard import (
    AdminDashboardResponse,
    DashboardUserStats,
    RecentGenerationItem,
    RecentLoginItem,
)
from app.services.tool_usage_service import build_tool_usage_payload

# ============================================================
# Constants
# ============================================================
ACTIVE_WINDOW_DAYS = 30
RECENT_LIMIT = 3


def _aware(dt: datetime | None) -> datetime | None:
    """Ensure datetime is timezone-aware (UTC)."""
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _safe_title(value: str | None, fallback: str) -> str:
    value = (value or "").strip()
    return value or fallback


class AdminDashboardService:
    """Read-only dashboard aggregator for the admin panel."""

    # ------------------------------------------------------------------
    # 1. STATS
    # ------------------------------------------------------------------
    @staticmethod
    def _active_user_ids(db: Session, since: datetime) -> set[int]:
        """Union of user_ids active (by any activity) since `since`."""
        active_ids: set[int] = set()

        sources: Iterable = (
            db.query(UserSession.user_id).filter(UserSession.created_at >= since),
            db.query(ContentGeneration.user_id).filter(ContentGeneration.created_at >= since),
            db.query(Campaign.user_id).filter(Campaign.created_at >= since),
            db.query(GrowthRecommendation.user_id).filter(GrowthRecommendation.created_at >= since),
        )
        for q in sources:
            active_ids.update(row[0] for row in q.distinct().all() if row[0] is not None)
        return active_ids

    @staticmethod
    def _build_stats(db: Session, since: datetime) -> DashboardUserStats:
        # Total (non-admin) users
        total_users: int = (
            db.query(func.count(User.id))
            .filter(User.role == "user")
            .scalar()
            or 0
        )

        # Suspended users
        suspended_users: int = (
            db.query(func.count(User.id))
            .filter(User.role == "user", User.is_suspended.is_(True))
            .scalar()
            or 0
        )

        # Active users (validated against role / suspension)
        active_ids = AdminDashboardService._active_user_ids(db, since)
        if active_ids:
            active_users = (
                db.query(func.count(User.id))
                .filter(
                    User.id.in_(active_ids),
                    User.role == "user",
                    User.is_suspended.is_(False),
                )
                .scalar()
                or 0
            )
        else:
            active_users = 0

        inactive_users = max(0, total_users - active_users - suspended_users)

        # 30-day generation counts
        def _count_30d(model) -> int:
            return (
                db.query(func.count(model.id))
                .filter(model.created_at >= since)
                .scalar()
                or 0
            )

        return DashboardUserStats(
            total_users=total_users,
            active_users=active_users,
            inactive_users=inactive_users,
            content_generations=_count_30d(ContentGeneration),
            campaign_generations=_count_30d(Campaign),
            growth_generations=_count_30d(GrowthRecommendation),
        )

    # ------------------------------------------------------------------
    # 2. RECENT GENERATIONS
    # ------------------------------------------------------------------
    @staticmethod
    def _recent_generations(db: Session) -> list[RecentGenerationItem]:
        items: list[dict] = []

        # --- Content ---
        for content, user in (
            db.query(ContentGeneration, User)
            .join(User, ContentGeneration.user_id == User.id)
            .order_by(desc(ContentGeneration.created_at))
            .limit(RECENT_LIMIT)
            .all()
        ):
            items.append(
                dict(
                    id=content.id,
                    user_id=user.id,
                    user_name=user.name,
                    user_email=user.email,
                    generation_type="content",
                    title=_safe_title(content.topic, "Untitled Content"),
                    created_at=_aware(content.created_at),
                )
            )

        # --- Campaigns ---
        for campaign, user in (
            db.query(Campaign, User)
            .join(User, Campaign.user_id == User.id)
            .order_by(desc(Campaign.created_at))
            .limit(RECENT_LIMIT)
            .all()
        ):
            items.append(
                dict(
                    id=campaign.id,
                    user_id=user.id,
                    user_name=user.name,
                    user_email=user.email,
                    generation_type="campaign",
                    title=_safe_title(campaign.campaign_name, "Untitled Campaign"),
                    created_at=_aware(campaign.created_at),
                )
            )

        # --- Growth Recommendations ---
        for rec, user in (
            db.query(GrowthRecommendation, User)
            .join(User, GrowthRecommendation.user_id == User.id)
            .order_by(desc(GrowthRecommendation.created_at))
            .limit(RECENT_LIMIT)
            .all()
        ):
            recs = rec.recommendations or []
            first_title = recs[0].get("title", "") if recs else ""
            items.append(
                dict(
                    id=rec.id,
                    user_id=user.id,
                    user_name=user.name,
                    user_email=user.email,
                    generation_type="growth",
                    title=_safe_title(first_title, "Growth Recommendations"),
                    created_at=_aware(rec.created_at),
                )
            )

        # Sort across all tools + keep top N
        items.sort(key=lambda x: x["created_at"], reverse=True)
        return [RecentGenerationItem(**i) for i in items[:RECENT_LIMIT]]

    # ------------------------------------------------------------------
    # 3. RECENT LOGINS
    # ------------------------------------------------------------------
    @staticmethod
    def _recent_logins(db: Session) -> list[RecentLoginItem]:
        latest_sessions_subq = (
            db.query(
                UserSession.user_id.label("user_id"),
                func.max(UserSession.created_at).label("latest_login"),
            )
            .group_by(UserSession.user_id)
            .subquery()
        )

        rows = (
            db.query(User, latest_sessions_subq.c.latest_login)
            .join(latest_sessions_subq, User.id == latest_sessions_subq.c.user_id)
            .filter(User.role == "user")
            .order_by(desc(latest_sessions_subq.c.latest_login))
            .limit(RECENT_LIMIT)
            .all()
        )

        return [
            RecentLoginItem(
                id=user.id,
                name=user.name,
                email=user.email,
                image=user.image,
                logged_in_at=_aware(latest_login),
            )
            for user, latest_login in rows
        ]

    # ------------------------------------------------------------------
    # PUBLIC
    # ------------------------------------------------------------------
    @staticmethod
    def get_dashboard(db: Session) -> AdminDashboardResponse:
        since = datetime.now(timezone.utc) - timedelta(days=ACTIVE_WINDOW_DAYS)

        stats = AdminDashboardService._build_stats(db, since)
        tool_usage = build_tool_usage_payload(db)
        recent_generations = AdminDashboardService._recent_generations(db)
        recent_logins = AdminDashboardService._recent_logins(db)

        return AdminDashboardResponse(
            stats=stats,
            tool_usage=tool_usage,
            recent_generations=recent_generations,
            recent_logins=recent_logins,
        )

