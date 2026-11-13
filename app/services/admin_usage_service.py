from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func, desc, asc, or_
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.content_generation import ContentGeneration
from app.models.campaign import Campaign
from app.models.growth_recommendation import GrowthRecommendation
from app.schemas.admin_usage import (
    UsageRecordItem,
    UsageRecordListResponse,
    UsageRecordDetail,
    UsageStatsResponse,
    UsageChartPoint,
    UsageChartResponse,
)

MODEL_MAP = {
    "content": ContentGeneration,
    "campaign": Campaign,
    "growth": GrowthRecommendation,
}

FEATURE_LABEL = {
    "content": "Content Generation",
    "campaign": "Campaign Planner",
    "growth": "Growth Recommendations",
}


def _aware(dt):
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _resolve_range(
    date_range: str,
    custom_from: Optional[datetime],
    custom_to: Optional[datetime],
) -> tuple[Optional[datetime], Optional[datetime]]:
    if date_range in ("all", "", None):
        return None, None
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if date_range == "today":
        return today_start, None
    if date_range == "week":
        return today_start - timedelta(days=6), None
    if date_range == "month":
        return today_start - timedelta(days=29), None
    if date_range == "year":
        return today_start - timedelta(days=364), None
    if date_range == "custom":
        return _aware(custom_from), _aware(custom_to)
    return None, None


def _first_title_from_recs(recs) -> str:
    if isinstance(recs, list) and recs and isinstance(recs[0], dict):
        return (recs[0].get("title") or "").strip() or "Growth Recommendations"
    return "Growth Recommendations"


def _apply_range(query, model, start, end):
    if start:
        query = query.filter(model.created_at >= start)
    if end:
        query = query.filter(model.created_at <= end)
    return query


class AdminUsageService:

    @staticmethod
    def list_records(
        db: Session,
        page: int = 1,
        page_size: int = 10,
        search: Optional[str] = None,
        sort: str = "latest",
        date_range: str = "all",
        custom_from: Optional[datetime] = None,
        custom_to: Optional[datetime] = None,
        feature: Optional[str] = None,
    ) -> UsageRecordListResponse:

        start, end = _resolve_range(date_range, custom_from, custom_to)
        order_fn = desc if sort == "latest" else asc

        def _build(model):
            q = db.query(model)
            q = _apply_range(q, model, start, end)
            if search and search.strip():
                term = f"%{search.strip()}%"
                q = q.join(User, model.user_id == User.id).filter(
                    or_(User.name.ilike(term), User.email.ilike(term))
                )
            return q

        active = [feature] if feature in MODEL_MAP else list(MODEL_MAP.keys())

        counts = {f: _build(MODEL_MAP[f]).count() for f in active}
        total = sum(counts.values())

        need = page * page_size
        rows = []
        for f in active:
            model = MODEL_MAP[f]
            for rec in _build(model).order_by(order_fn(model.created_at)).limit(need).all():
                rows.append((f, rec))

        rows.sort(key=lambda x: _aware(x[1].created_at), reverse=(sort == "latest"))

        start_idx = (page - 1) * page_size
        sliced = rows[start_idx:start_idx + page_size]

        user_ids = {rec.user_id for _, rec in sliced}
        users_map = {}
        if user_ids:
            for u in db.query(User).filter(User.id.in_(user_ids)).all():
                users_map[u.id] = u

        items: list[UsageRecordItem] = []
        for f, rec in sliced:
            u = users_map.get(rec.user_id)
            if not u:
                continue
            if f == "content":
                title = (rec.topic or "Untitled Content").strip()
            elif f == "campaign":
                title = (rec.campaign_name or "Untitled Campaign").strip()
            else:
                title = _first_title_from_recs(rec.recommendations)
            items.append(
                UsageRecordItem(
                    id=rec.id,
                    user_id=u.id,
                    user_name=u.name,
                    user_email=u.email,
                    user_image=u.image,
                    feature=f,
                    title=title,
                    status="success",
                    created_at=_aware(rec.created_at),
                )
            )

        total_pages = max(1, (total + page_size - 1) // page_size)

        return UsageRecordListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    @staticmethod
    def get_detail(db: Session, feature: str, record_id: int) -> UsageRecordDetail:
        model = MODEL_MAP.get(feature)
        if not model:
            raise HTTPException(status_code=400, detail="Invalid feature")

        rec = db.query(model).filter(model.id == record_id).first()
        if not rec:
            raise HTTPException(status_code=404, detail="Record not found")

        user = db.query(User).filter(User.id == rec.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if feature == "content":
            title = (rec.topic or "Untitled Content").strip()
            input_payload = {
                "platform": rec.platform,
                "content_type": rec.content_type,
                "topic": rec.topic,
                "target_audience": rec.target_audience or [],
                "tone": rec.tone,
                "language": rec.language,
                "notes": rec.notes,
            }
            output_payload = rec.generated_content or ""
        elif feature == "campaign":
            title = (rec.campaign_name or "Untitled Campaign").strip()
            input_payload = {
                "objective": rec.objective,
                "product_service": rec.product_service,
                "target_audience": rec.target_audience or [],
                "channels": rec.channels or [],
                "budget": rec.budget,
                "currency": rec.currency,
                "start_date": str(rec.start_date) if rec.start_date else None,
                "end_date": str(rec.end_date) if rec.end_date else None,
                "tone": rec.tone,
                "notes": rec.notes,
            }
            output_payload = rec.generated_plan or {}
        else:
            title = _first_title_from_recs(rec.recommendations)
            input_payload = {
                "business_goals": rec.business_goals,
                "challenges": rec.challenges,
                "target_audience": rec.target_audience or [],
                "ai_instruction": rec.ai_instruction,
            }
            output_payload = rec.recommendations or []

        return UsageRecordDetail(
            id=rec.id,
            user_id=user.id,
            user_name=user.name,
            user_email=user.email,
            user_image=user.image,
            feature=feature,
            title=title,
            status="success",
            created_at=_aware(rec.created_at),
            input_payload=input_payload,
            output_payload=output_payload,
        )

    @staticmethod
    def get_stats(
        db: Session,
        date_range: str = "all",
        custom_from: Optional[datetime] = None,
        custom_to: Optional[datetime] = None,
        feature: Optional[str] = None,
    ) -> UsageStatsResponse:
        start, end = _resolve_range(date_range, custom_from, custom_to)
        active = [feature] if feature in MODEL_MAP else list(MODEL_MAP.keys())

        counts: dict[str, int] = {"content": 0, "campaign": 0, "growth": 0}

        for f in active:
            model = MODEL_MAP[f]
            q = db.query(func.count(model.id))
            q = _apply_range(q, model, start, end)
            counts[f] = q.scalar() or 0

        total = sum(counts.values())

        return UsageStatsResponse(
            total_generations=total,
            content_generations=counts["content"],
            campaign_generations=counts["campaign"],
            growth_generations=counts["growth"],
        )
    




    @staticmethod
    def get_chart(
        db: Session,
        date_range: str = "all",
        custom_from: Optional[datetime] = None,
        custom_to: Optional[datetime] = None,
        feature: Optional[str] = None,
    ) -> UsageChartResponse:
        start, end = _resolve_range(date_range, custom_from, custom_to)
        active = [feature] if feature in MODEL_MAP else list(MODEL_MAP.keys())

        now = datetime.now(timezone.utc)

        if start and end:
            from_dt, to_dt = start, end
        elif start:
            from_dt, to_dt = start, now
        elif end:
            from_dt, to_dt = end - timedelta(days=29), end
        else:
            earliest = None
            for f in active:
                model = MODEL_MAP[f]
                r = db.query(func.min(model.created_at)).scalar()
                if r and (earliest is None or r < earliest):
                    earliest = r
            if earliest is None:
                return UsageChartResponse(points=[], totals={f: 0 for f in active})
            from_dt = _aware(earliest)
            to_dt = now

        from_dt = from_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        to_dt = to_dt.replace(hour=23, minute=59, second=59, microsecond=999999)

        span_days = (to_dt.date() - from_dt.date()).days + 1

        if span_days <= 31:
            bucket = "day"
        elif span_days <= 120:
            bucket = "week"
        else:
            bucket = "month"

        totals: dict[str, int] = {f: 0 for f in active}
        raw_rows: list[tuple[str, str, int]] = []

        for f in active:
            model = MODEL_MAP[f]
            if bucket == "day":
                expr = func.date(model.created_at)
            elif bucket == "week":
                expr = func.date_format(model.created_at, "%x-W%v")
            else:
                expr = func.date_format(model.created_at, "%Y-%m")

            rows = (
                db.query(expr.label("bucket"), func.count(model.id).label("c"))
                .filter(model.created_at >= from_dt, model.created_at <= to_dt)
                .group_by(expr)
                .all()
            )
            for row in rows:
                raw_rows.append((str(row.bucket), f, row.c))
                totals[f] += row.c

        bucket_labels: dict[str, str] = {}
        if bucket == "day":
            cursor = from_dt
            while cursor <= to_dt:
                key = cursor.strftime("%Y-%m-%d")
                bucket_labels[key] = cursor.strftime("%b %d")
                cursor += timedelta(days=1)
        elif bucket == "week":
            cursor = from_dt - timedelta(days=from_dt.weekday())
            while cursor <= to_dt:
                iso_year, iso_week, _ = cursor.isocalendar()
                key = f"{iso_year:04d}-W{iso_week:02d}"
                bucket_labels[key] = f"W{iso_week} '{str(iso_year)[2:]}"
                cursor += timedelta(days=7)
        else:
            cursor = from_dt.replace(day=1)
            while cursor <= to_dt:
                key = cursor.strftime("%Y-%m")
                bucket_labels[key] = cursor.strftime("%b %y")
                if cursor.month == 12:
                    cursor = cursor.replace(year=cursor.year + 1, month=1)
                else:
                    cursor = cursor.replace(month=cursor.month + 1)

        buckets: dict[str, dict[str, int]] = {
            key: {f: 0 for f in active} for key in bucket_labels
        }
        for key, f, count in raw_rows:
            if key in buckets:
                buckets[key][f] = count

        points: list[UsageChartPoint] = []
        for key, label in bucket_labels.items():
            counts = buckets[key]
            points.append(
                UsageChartPoint(
                    date=label,
                    content=counts.get("content", 0),
                    campaign=counts.get("campaign", 0),
                    growth=counts.get("growth", 0),
                    failed=0,
                )
            )

        return UsageChartResponse(points=points, totals=totals)
    