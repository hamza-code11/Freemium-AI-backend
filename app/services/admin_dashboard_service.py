from datetime import datetime, timedelta, timezone
from typing import Optional, Iterable

from sqlalchemy import desc, func, union_all, literal_column, select
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.user_session import UserSession
from app.models.content_generation import ContentGeneration
from app.models.campaign import Campaign
from app.models.growth_recommendation import GrowthRecommendation
from app.schemas.admin_dashboard import (
    AdminDashboardResponse, DashboardUserStats, RecentGenerationItem, RecentLoginItem,
    ChartPoint, UserGrowthChart, AIGenerationSeries, AIGenerationChart,
)
from app.services.tool_usage_service import build_tool_usage_payload


ACTIVE_WINDOW_DAYS = 30
RECENT_LIMIT = 3
MAX_CHART_POINTS = 31


def _aware(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

def _safe_title(value: Optional[str], fallback: str) -> str:
    value = (value or "").strip()
    return value or fallback

def _resolve_range(date_range: str, custom_from: Optional[datetime], custom_to: Optional[datetime]) -> tuple[Optional[datetime], Optional[datetime]]:
    if date_range in ("all", "", None):
        return None, None
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if date_range == "today": return today_start, None
    if date_range == "week": return today_start - timedelta(days=6), None
    if date_range == "month": return today_start - timedelta(days=29), None
    if date_range == "year": return today_start - timedelta(days=364), None
    if date_range == "custom": return _aware(custom_from), _aware(custom_to)
    return None, None

def _bucket_mode(db: Session, start: Optional[datetime], end: Optional[datetime]) -> tuple[str, datetime, datetime]:
    now = datetime.now(timezone.utc)
    if start and end:
        from_dt, to_dt = start, end
    elif start:
        from_dt, to_dt = start, now
    elif end:
        from_dt, to_dt = end - timedelta(days=29), end
    else:
        # Optimization: Min dates nikaalne ke liye single queries
        min_user = db.query(func.min(User.created_at)).filter(User.role == "user").scalar()
        min_content = db.query(func.min(ContentGeneration.created_at)).scalar()
        min_campaign = db.query(func.min(Campaign.created_at)).scalar()
        min_growth = db.query(func.min(GrowthRecommendation.created_at)).scalar()

        candidates = [x for x in (min_user, min_content, min_campaign, min_growth) if x]
        from_dt = _aware(min(candidates)) if candidates else (now - timedelta(days=29))
        to_dt = now

    from_dt = from_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    to_dt = to_dt.replace(hour=23, minute=59, second=59, microsecond=999999)

    span = (to_dt.date() - from_dt.date()).days + 1
    mode = "day" if span <= MAX_CHART_POINTS else "week" if span <= 120 else "month"
    return mode, from_dt, to_dt

def _iter_buckets(mode: str, from_dt: datetime, to_dt: datetime) -> list[tuple[str, str]]:
    out = []
    if mode == "day":
        cursor = from_dt
        while cursor <= to_dt:
            out.append((cursor.strftime("%Y-%m-%d"), cursor.strftime("%b %d")))
            cursor += timedelta(days=1)
    elif mode == "week":
        cursor = from_dt - timedelta(days=from_dt.weekday())
        while cursor <= to_dt:
            iso = cursor.isocalendar()
            out.append((f"{iso[0]:04d}-W{iso[1]:02d}", f"W{iso[1]} '{str(iso[0])[2:]}"))
            cursor += timedelta(days=7)
    else:
        cursor = from_dt.replace(day=1)
        while cursor <= to_dt:
            out.append((cursor.strftime("%Y-%m"), cursor.strftime("%b %y")))
            cursor = cursor.replace(year=cursor.year + 1, month=1) if cursor.month == 12 else cursor.replace(month=cursor.month + 1)
    return out

def _bucket_expr(mode: str, column):
    if mode == "day": return func.date(column)
    if mode == "week": return func.date_format(column, "%x-W%v")
    return func.date_format(column, "%Y-%m")


class AdminDashboardService:

    @staticmethod
    def _build_stats(db: Session, since: datetime, start: Optional[datetime], end: Optional[datetime]) -> DashboardUserStats:
        # 1. User Stats
        users_q = db.query(func.count(User.id)).filter(User.role == "user")
        if start: users_q = users_q.filter(User.created_at >= start)
        if end: users_q = users_q.filter(User.created_at <= end)
        total_users = users_q.scalar() or 0

        suspended_q = db.query(func.count(User.id)).filter(User.role == "user", User.is_suspended.is_(True))
        if start: suspended_q = suspended_q.filter(User.created_at >= start)
        if end: suspended_q = suspended_q.filter(User.created_at <= end)
        suspended_users = suspended_q.scalar() or 0

        # 2. Active Users (SQL Level Subquery for Speed)
        content_subq = db.query(ContentGeneration.user_id).filter(ContentGeneration.created_at >= since)
        campaign_subq = db.query(Campaign.user_id).filter(Campaign.created_at >= since)
        growth_subq = db.query(GrowthRecommendation.user_id).filter(GrowthRecommendation.created_at >= since)
        session_subq = db.query(UserSession.user_id).filter(UserSession.created_at >= since)

        active_ids_query = union_all(content_subq, campaign_subq, growth_subq, session_subq).subquery()
        
        active_users = (
            db.query(func.count(func.distinct(User.id)))
            .filter(
                User.role == "user",
                User.is_suspended.is_(False),
                User.id.in_(select(active_ids_query.c[0]))
            )
            .scalar() or 0
        )

        inactive_users = max(0, total_users - active_users - suspended_users)

        # 3. Generations (Single Query using UNION ALL)
        c_q = db.query(func.count(ContentGeneration.id).label("c")).filter(ContentGeneration.created_at >= start if start else True, ContentGeneration.created_at <= end if end else True)
        cp_q = db.query(func.count(Campaign.id).label("cp")).filter(Campaign.created_at >= start if start else True, Campaign.created_at <= end if end else True)
        g_q = db.query(func.count(GrowthRecommendation.id).label("g")).filter(GrowthRecommendation.created_at >= start if start else True, GrowthRecommendation.created_at <= end if end else True)
        
        # Combine counts efficiently
        c_count = c_q.scalar() or 0
        cp_count = cp_q.scalar() or 0
        g_count = g_q.scalar() or 0

        return DashboardUserStats(
            total_users=total_users,
            active_users=active_users,
            inactive_users=inactive_users,
            content_generations=c_count,
            campaign_generations=cp_count,
            growth_generations=g_count,
        )

    @staticmethod
    def _recent_generations(db: Session) -> list[RecentGenerationItem]:
        items = []
        for content, user in db.query(ContentGeneration, User).join(User, ContentGeneration.user_id == User.id).order_by(desc(ContentGeneration.created_at)).limit(RECENT_LIMIT).all():
            items.append(dict(id=content.id, user_id=user.id, user_name=user.name, user_email=user.email, generation_type="content", title=_safe_title(content.topic, "Untitled Content"), created_at=_aware(content.created_at)))

        for campaign, user in db.query(Campaign, User).join(User, Campaign.user_id == User.id).order_by(desc(Campaign.created_at)).limit(RECENT_LIMIT).all():
            items.append(dict(id=campaign.id, user_id=user.id, user_name=user.name, user_email=user.email, generation_type="campaign", title=_safe_title(campaign.campaign_name, "Untitled Campaign"), created_at=_aware(campaign.created_at)))

        for rec, user in db.query(GrowthRecommendation, User).join(User, GrowthRecommendation.user_id == User.id).order_by(desc(GrowthRecommendation.created_at)).limit(RECENT_LIMIT).all():
            recs = rec.recommendations or []
            first_title = recs[0].get("title", "") if recs else ""
            items.append(dict(id=rec.id, user_id=user.id, user_name=user.name, user_email=user.email, generation_type="growth", title=_safe_title(first_title, "Growth Recommendations"), created_at=_aware(rec.created_at)))

        items.sort(key=lambda x: x["created_at"], reverse=True)
        return [RecentGenerationItem(**i) for i in items[:RECENT_LIMIT]]

    @staticmethod
    def _recent_logins(db: Session) -> list[RecentLoginItem]:
        latest_sessions_subq = db.query(UserSession.user_id.label("user_id"), func.max(UserSession.created_at).label("latest_login")).group_by(UserSession.user_id).subquery()
        rows = db.query(User, latest_sessions_subq.c.latest_login).join(latest_sessions_subq, User.id == latest_sessions_subq.c.user_id).filter(User.role == "user").order_by(desc(latest_sessions_subq.c.latest_login)).limit(RECENT_LIMIT).all()
        return [RecentLoginItem(id=user.id, name=user.name, email=user.email, image=user.image, logged_in_at=_aware(latest_login)) for user, latest_login in rows]

    @staticmethod
    def _user_growth_chart(db: Session, mode: str, from_dt: datetime, to_dt: datetime) -> UserGrowthChart:
        expr = _bucket_expr(mode, User.created_at)
        rows = db.query(expr.label("bucket"), func.count(User.id).label("c")).filter(User.role == "user", User.created_at >= from_dt, User.created_at <= to_dt).group_by(expr).all()
        counts = {str(row.bucket): row.c for row in rows}

        points, total = [], 0
        for key, label in _iter_buckets(mode, from_dt, to_dt):
            v = counts.get(key, 0)
            points.append(ChartPoint(label=label, value=v))
            total += v
        return UserGrowthChart(points=points, totals=total)

    @staticmethod
    def _ai_generation_chart(db: Session, mode: str, from_dt: datetime, to_dt: datetime) -> AIGenerationChart:
        models = {"content": ContentGeneration, "campaign": Campaign, "growth": GrowthRecommendation}
        bucket_labels = _iter_buckets(mode, from_dt, to_dt)
        labels = [lbl for _, lbl in bucket_labels]
        keys = [k for k, _ in bucket_labels]

        totals = {"content": 0, "campaign": 0, "growth": 0}
        series_map = {"content": {}, "campaign": {}, "growth": {}}

        for name, model in models.items():
            expr = _bucket_expr(mode, model.created_at)
            rows = db.query(expr.label("bucket"), func.count(model.id).label("c")).filter(model.created_at >= from_dt, model.created_at <= to_dt).group_by(expr).all()
            for row in rows:
                k = str(row.bucket)
                series_map[name][k] = row.c
                totals[name] += row.c

        series = []
        for name in ("content", "campaign", "growth"):
            pts = [ChartPoint(label=lbl, value=series_map[name].get(key, 0)) for key, lbl in zip(keys, labels)]
            series.append(AIGenerationSeries(name=name, points=pts))

        return AIGenerationChart(labels=labels, series=series, totals=totals, combined_total=sum(totals.values()))

    @staticmethod
    def get_dashboard(db: Session, date_range: str = "all", custom_from: Optional[datetime] = None, custom_to: Optional[datetime] = None) -> AdminDashboardResponse:
        active_since = datetime.now(timezone.utc) - timedelta(days=ACTIVE_WINDOW_DAYS)
        start, end = _resolve_range(date_range, custom_from, custom_to)
        mode, from_dt, to_dt = _bucket_mode(db, start, end)

        stats = AdminDashboardService._build_stats(db, active_since, start, end)
        
        return AdminDashboardResponse(
            stats=stats,
            tool_usage=build_tool_usage_payload(db),
            recent_generations=AdminDashboardService._recent_generations(db),
            recent_logins=AdminDashboardService._recent_logins(db),
            user_growth_chart=AdminDashboardService._user_growth_chart(db, mode, from_dt, to_dt),
            ai_generation_chart=AdminDashboardService._ai_generation_chart(db, mode, from_dt, to_dt),
        )


    