# app/services/dashboard_service.py

from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy import or_, func
from sqlalchemy.orm import Session

from app.models.campaign import Campaign
from app.models.content_generation import ContentGeneration
from app.models.growth_recommendation import GrowthRecommendation
from app.schemas.dashboard import (
    DashboardResponse,
    DashboardStats,
    DashboardHistoryItem,
    UsageChartData,
    BreakdownItem,
)


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _truncate(text: str | None, length: int = 150) -> str:
    if not text:
        return ""
    text = str(text)
    return text[:length] + ("..." if len(text) > length else "")


class DashboardService:

    @staticmethod
    def get_dashboard(
        db: Session, 
        user_id: int,
        range_type: str = "week",
        custom_from: Optional[datetime] = None,
        custom_to: Optional[datetime] = None,
    ) -> DashboardResponse:
        
        # ----- 1. STATS (always full) -----
        content_count = db.query(func.count(ContentGeneration.id)).filter(
            ContentGeneration.user_id == user_id
        ).scalar() or 0

        campaign_count = db.query(func.count(Campaign.id)).filter(
            Campaign.user_id == user_id
        ).scalar() or 0

        rec_count = db.query(func.count(GrowthRecommendation.id)).filter(
            GrowthRecommendation.user_id == user_id
        ).scalar() or 0

        stats = DashboardStats(
            total_generations=content_count + campaign_count + rec_count,
            content_generated=content_count,
            campaigns_generated=campaign_count,
            recommendations_generated=rec_count,
        )

        # ----- 2. RECENT CONTENT (4) -----
        recent_content = []
        content_query = (
            db.query(ContentGeneration)
            .filter(ContentGeneration.user_id == user_id)
            .order_by(ContentGeneration.created_at.desc())
            .limit(4)
            .all()
        )
        for c in content_query:
            recent_content.append(DashboardHistoryItem(
                id=c.id, type="content",
                title=c.topic or "Untitled Content",
                preview=_truncate(c.generated_content, 150),
                content=None,
                created_at=_aware(c.created_at),
                metadata={
                    "platform": c.platform,
                    "content_type": c.content_type,
                    "tone": c.tone,
                    "language": c.language,
                },
            ))

        # ----- 3. RECENT CAMPAIGNS (3) -----
        recent_campaigns = []
        campaign_query = (
            db.query(Campaign)
            .filter(Campaign.user_id == user_id)
            .order_by(Campaign.created_at.desc())
            .limit(3)
            .all()
        )
        for c in campaign_query:
            plan = c.generated_plan or {}
            recent_campaigns.append(DashboardHistoryItem(
                id=c.id, type="campaign",
                title=c.campaign_name or "Untitled Campaign",
                preview=_truncate(plan.get("strategy") or plan.get("description"), 150),
                content=None,
                created_at=_aware(c.created_at),
                metadata={
                    "objective": c.objective,
                    "channels": c.channels or [],
                    "generated_plan": plan,
                    "product_service": c.product_service,
                    "target_audience": c.target_audience or [],
                    "budget": c.budget,
                    "currency": c.currency,
                    "start_date": c.start_date.isoformat() if c.start_date else None,
                    "end_date": c.end_date.isoformat() if c.end_date else None,
                    "tone": c.tone,
                    "notes": c.notes,
                },
            ))

        # ----- 4. RECENT RECOMMENDATIONS (3) -----
        recent_recommendations = []
        rec_query = (
            db.query(GrowthRecommendation)
            .filter(GrowthRecommendation.user_id == user_id)
            .order_by(GrowthRecommendation.created_at.desc())
            .limit(3)
            .all()
        )
        for r in rec_query:
            recs = r.recommendations or []
            first_title = recs[0].get("title", "") if recs else "Growth Recommendations"
            recent_recommendations.append(DashboardHistoryItem(
                id=r.id, type="recommendation",
                title=first_title,
                preview=f"{len(recs)} recommendations generated",
                content=None,
                created_at=_aware(r.created_at),
                metadata={
                    "count": len(recs),
                    "recommendations": recs,
                    "business_goals": r.business_goals,
                    "challenges": r.challenges,
                    "target_audience": r.target_audience or [],
                    "ai_instruction": r.ai_instruction,
                },
            ))

        # ----- 5. USAGE CHART (dynamic range) -----
        usage_chart = DashboardService._get_usage_chart(
            db, user_id, range_type, custom_from, custom_to
        )

        # ----- 6. BREAKDOWN (dynamic range) -----
        breakdown = DashboardService._get_breakdown(
            db, user_id, range_type, custom_from, custom_to
        )

        return DashboardResponse(
            stats=stats,
            recent_content=recent_content,
            recent_campaigns=recent_campaigns,
            recent_recommendations=recent_recommendations,
            usage_chart=usage_chart,
            breakdown=breakdown,
        )

    # 🔥 Date range helper
    @staticmethod
    def _get_date_range(
        range_type: str,
        custom_from: Optional[datetime] = None,
        custom_to: Optional[datetime] = None,
    ):
        now = datetime.now(timezone.utc)
        
        if range_type == "today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            return start, now, "hour"
        elif range_type == "week":
            return now - timedelta(days=7), now, "day"
        elif range_type == "month":
            return now - timedelta(days=30), now, "day"
        elif range_type == "year":
            return now - timedelta(days=365), now, "month"
        elif range_type == "all":
            return None, None, "year"
        elif range_type == "custom" and custom_from:
            return _aware(custom_from), _aware(custom_to) or now, "day"
        else:
            return now - timedelta(days=7), now, "day"

    # 🔥 Usage Chart
    @staticmethod
    def _get_usage_chart(
        db: Session, user_id: int, range_type: str,
        custom_from: Optional[datetime] = None,
        custom_to: Optional[datetime] = None,
    ) -> UsageChartData:
        
        start_date, end_date, granularity = DashboardService._get_date_range(
            range_type, custom_from, custom_to
        )
        
        labels = []
        values = []

        # 🔥 Today → hourly
        if granularity == "hour":
            now = datetime.now(timezone.utc)
            for i in range(23, -1, -6):  # 0, 6, 12, 18 hours
                hour_start = now.replace(hour=i, minute=0, second=0, microsecond=0)
                hour_end = hour_start + timedelta(hours=6)
                
                total = DashboardService._count_in_range(
                    db, user_id, hour_start, hour_end
                )
                labels.append(f"{i:02d}:00")
                values.append(total)

        # 🔥 Last N days
        elif granularity == "day":
            if not start_date:
                start_date = datetime.now(timezone.utc) - timedelta(days=7)
            days = (end_date - start_date).days
            if days < 1:
                days = 1
            if days > 30:
                days = 30  # Max 30 days

            for i in range(days, -1, -1):
                day_start = (datetime.now(timezone.utc) - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
                day_end = day_start + timedelta(days=1)
                
                total = DashboardService._count_in_range(db, user_id, day_start, day_end)
                labels.append(day_start.strftime('%b %d'))
                values.append(total)

        # 🔥 Last N months
        else:
            now = datetime.now(timezone.utc)
            for i in range(11, -1, -1):
                # Pehle mahine ka start
                month_start = (now.replace(day=1) - timedelta(days=30 * i)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                # Agle mahine ka start
                if month_start.month == 12:
                    month_end = month_start.replace(year=month_start.year + 1, month=1)
                else:
                    month_end = month_start.replace(month=month_start.month + 1)
                
                total = DashboardService._count_in_range(db, user_id, month_start, month_end)
                labels.append(month_start.strftime('%b'))
                values.append(total)

        return UsageChartData(labels=labels, values=values)

    @staticmethod
    def _count_in_range(db: Session, user_id: int, start, end) -> int:
        """Count total generations in a date range."""
        content = db.query(func.count(ContentGeneration.id)).filter(
            ContentGeneration.user_id == user_id,
            ContentGeneration.created_at >= start,
            ContentGeneration.created_at < end,
        ).scalar() or 0

        campaigns = db.query(func.count(Campaign.id)).filter(
            Campaign.user_id == user_id,
            Campaign.created_at >= start,
            Campaign.created_at < end,
        ).scalar() or 0

        recs = db.query(func.count(GrowthRecommendation.id)).filter(
            GrowthRecommendation.user_id == user_id,
            GrowthRecommendation.created_at >= start,
            GrowthRecommendation.created_at < end,
        ).scalar() or 0

        return content + campaigns + recs

    # 🔥 Breakdown
    @staticmethod
    def _get_breakdown(
        db: Session, user_id: int, range_type: str,
        custom_from: Optional[datetime] = None,
        custom_to: Optional[datetime] = None,
    ) -> list[BreakdownItem]:
        
        start_date, end_date, _ = DashboardService._get_date_range(
            range_type, custom_from, custom_to
        )

        # Build filters
        content_filter = [ContentGeneration.user_id == user_id]
        campaign_filter = [Campaign.user_id == user_id]
        rec_filter = [GrowthRecommendation.user_id == user_id]

        if start_date:
            content_filter.append(ContentGeneration.created_at >= start_date)
            campaign_filter.append(Campaign.created_at >= start_date)
            rec_filter.append(GrowthRecommendation.created_at >= start_date)
        
        if end_date:
            content_filter.append(ContentGeneration.created_at <= end_date)
            campaign_filter.append(Campaign.created_at <= end_date)
            rec_filter.append(GrowthRecommendation.created_at <= end_date)

        content_count = db.query(func.count(ContentGeneration.id)).filter(*content_filter).scalar() or 0
        campaign_count = db.query(func.count(Campaign.id)).filter(*campaign_filter).scalar() or 0
        rec_count = db.query(func.count(GrowthRecommendation.id)).filter(*rec_filter).scalar() or 0

        return [
            BreakdownItem(label="Content Generated", value=content_count, color="#3B82F6"),
            BreakdownItem(label="Campaigns", value=campaign_count, color="#8B5CF6"),
            BreakdownItem(label="Growth Recommendations", value=rec_count, color="#10B981"),
        ]