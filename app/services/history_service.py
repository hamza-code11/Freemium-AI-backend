# app/services/history_service.py

from datetime import datetime, timedelta, timezone
from sqlalchemy import or_, func
from sqlalchemy.orm import Session

from app.models.campaign import Campaign
from app.models.content_generation import ContentGeneration
from app.models.growth_recommendation import GrowthRecommendation
from app.schemas.history import HistoryItem, HistoryResponse, HistoryStats


# ============================================
# HELPERS
# ============================================
def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _parse_date_range(date_range: str) -> datetime | None:
    if date_range in ("all", "", None):
        return None
    now = datetime.now(timezone.utc)
    mapping = {
        "today": now.replace(hour=0, minute=0, second=0, microsecond=0),
        "week": now - timedelta(days=7),
        "month": now - timedelta(days=30),
        "year": now - timedelta(days=365),
    }
    return mapping.get(date_range)


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return _aware(dt).isoformat()


def _truncate(text: str | None, length: int = 150) -> str:
    if not text:
        return ""
    text = str(text)
    return text[:length] + ("..." if len(text) > length else "")


# ============================================
# HISTORY SERVICE
# ============================================
class HistoryService:

    @staticmethod
    def get_stats(db: Session, user_id: int) -> HistoryStats:
        content_count = db.query(func.count(ContentGeneration.id)).filter(
            ContentGeneration.user_id == user_id
        ).scalar() or 0

        campaign_count = db.query(func.count(Campaign.id)).filter(
            Campaign.user_id == user_id
        ).scalar() or 0

        rec_count = db.query(func.count(GrowthRecommendation.id)).filter(
            GrowthRecommendation.user_id == user_id
        ).scalar() or 0

        return HistoryStats(
            total_generations=content_count + campaign_count + rec_count,
            content_generated=content_count,
            campaigns_generated=campaign_count,
            recommendations_generated=rec_count,
        )

    @staticmethod
    def get_history(
        db: Session,
        user_id: int,
        type_filter: str = "all",
        date_range: str = "all",
        custom_from: datetime | None = None,
        custom_to: datetime | None = None,
        sort: str = "latest",
        search: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> HistoryResponse:
        
        all_items: list[HistoryItem] = []
        search_str = (search or "").strip().lower()

        # ---------- 1. CONTENT ----------
        if type_filter in ("all", "content"):
            all_items.extend(
                HistoryService._fetch_content(db, user_id, search_str)
            )

        # ---------- 2. CAMPAIGNS ----------
        if type_filter in ("all", "campaign"):
            all_items.extend(
                HistoryService._fetch_campaigns(db, user_id, search_str)
            )

        # ---------- 3. RECOMMENDATIONS ----------
        if type_filter in ("all", "recommendation"):
            all_items.extend(
                HistoryService._fetch_recommendations(db, user_id)
            )

        # ---------- 4. DATE FILTER ----------
        cutoff = _parse_date_range(date_range)
        if cutoff:
            all_items = [i for i in all_items if i.created_at and i.created_at >= cutoff]
        if date_range == "custom":
            if custom_from:
                cf = _aware(custom_from)
                all_items = [i for i in all_items if i.created_at and i.created_at >= cf]
            if custom_to:
                ct = _aware(custom_to)
                all_items = [i for i in all_items if i.created_at and i.created_at <= ct]

        # ---------- 5. SORT ----------
        all_items.sort(
            key=lambda x: x.created_at or datetime.min.replace(tzinfo=timezone.utc),
            reverse=(sort == "latest"),
        )

        # ---------- 6. PAGINATION ----------
        total = len(all_items)
        total_pages = max(1, (total + page_size - 1) // page_size)
        start = (page - 1) * page_size
        end = start + page_size
        paginated = all_items[start:end]

        return HistoryResponse(
            items=paginated,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    # ============================================
    # PRIVATE FETCHERS
    # ============================================
    @staticmethod
    def _fetch_content(db: Session, user_id: int, search: str) -> list[HistoryItem]:
        q = db.query(ContentGeneration).filter(ContentGeneration.user_id == user_id)
        if search:
            q = q.filter(or_(
                ContentGeneration.topic.ilike(f"%{search}%"),
                ContentGeneration.generated_content.ilike(f"%{search}%"),
            ))
        results = []
        for c in q.all():
            results.append(HistoryItem(
                id=c.id,
                type="content",
                title=c.topic or "Untitled Content",
                preview=_truncate(c.generated_content, 150),
                content=c.generated_content,
                created_at=_aware(c.created_at),
                metadata={
                    "platform": c.platform,
                    "content_type": c.content_type,
                    "tone": c.tone,
                    "language": c.language,
                    "notes": c.notes,
                    "target_audience": c.target_audience or [],
                },
            ))
        return results

    @staticmethod
    def _fetch_campaigns(db: Session, user_id: int, search: str) -> list[HistoryItem]:
        q = db.query(Campaign).filter(Campaign.user_id == user_id)
        if search:
            q = q.filter(or_(
                Campaign.campaign_name.ilike(f"%{search}%"),
                Campaign.objective.ilike(f"%{search}%"),
            ))
        results = []
        for c in q.all():
            plan = c.generated_plan or {}
            results.append(HistoryItem(
                id=c.id,
                type="campaign",
                title=c.campaign_name or "Untitled Campaign",
                preview=_truncate(plan.get("strategy") or plan.get("description"), 150),
                content=None,
                created_at=_aware(c.created_at),
                metadata={
                    "objective": c.objective,
                    "product_service": c.product_service,
                    "target_audience": c.target_audience or [],
                    "channels": c.channels or [],
                    "budget": c.budget,
                    "currency": c.currency,
                    "start_date": _iso(c.start_date),
                    "end_date": _iso(c.end_date),
                    "tone": c.tone,
                    "notes": c.notes,
                    "generated_plan": plan,
                },
            ))
        return results

    @staticmethod
    def _fetch_recommendations(db: Session, user_id: int) -> list[HistoryItem]:
        q = db.query(GrowthRecommendation).filter(
            GrowthRecommendation.user_id == user_id
        )
        results = []
        for r in q.all():
            recs = r.recommendations or []
            first_title = recs[0].get("title", "") if recs else "Growth Recommendations"
            results.append(HistoryItem(
                id=r.id,
                type="recommendation",
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
        return results
    