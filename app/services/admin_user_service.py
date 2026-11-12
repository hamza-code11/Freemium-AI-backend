# app/services/admin_user_service.py

from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy import func, desc, asc, or_
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.user_session import UserSession
from app.models.content_generation import ContentGeneration
from app.models.campaign import Campaign
from app.models.growth_recommendation import GrowthRecommendation
from app.schemas.admin_user import (
    AdminUserItem, AdminUserListResponse, AdminUserDetail,
)


def _aware(dt):
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


class AdminUserService:

    @staticmethod
    def list_users(
        db: Session,
        page: int = 1,
        page_size: int = 10,
        search: Optional[str] = None,
        status: str = "all",
        sort: str = "latest",
        date_range: str = "all",
        custom_from: Optional[datetime] = None,
        custom_to: Optional[datetime] = None,
    ) -> AdminUserListResponse:
        
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)

        # 🔥 1. Base query
        query = db.query(User).filter(User.role == "user")

        # 🔥 2. Search
        if search and search.strip():
            term = f"%{search.strip()}%"
            query = query.filter(or_(
                User.name.ilike(term),
                User.email.ilike(term),
            ))

        # 🔥 3. Date range (based on created_at)
        cutoff = _parse_date_range(date_range)
        if cutoff:
            query = query.filter(User.created_at >= cutoff)
        
        if date_range == "custom":
            if custom_from:
                query = query.filter(User.created_at >= _aware(custom_from))
            if custom_to:
                query = query.filter(User.created_at <= _aware(custom_to))

        # 🔥 4. Status filter (suspended is easy in DB)
        if status == "suspended":
            query = query.filter(User.is_suspended == True)

        # 🔥 5. Active/Inactive filter (DB-level using activity subqueries)
        if status in ("active", "inactive"):
            # Subqueries: active users in last 30 days
            active_user_subq = (
                db.query(ContentGeneration.user_id)
                .filter(ContentGeneration.created_at >= thirty_days_ago)
                .union(
                    db.query(Campaign.user_id)
                    .filter(Campaign.created_at >= thirty_days_ago)
                )
                .union(
                    db.query(GrowthRecommendation.user_id)
                    .filter(GrowthRecommendation.created_at >= thirty_days_ago)
                )
                .union(
                    db.query(UserSession.user_id)
                    .filter(UserSession.created_at >= thirty_days_ago)
                )
                .subquery()
            )

            if status == "active":
                query = query.filter(
                    User.is_suspended == False,
                    User.id.in_(active_user_subq),
                )
            else:  # inactive
                query = query.filter(
                    User.is_suspended == False,
                    User.id.notin_(active_user_subq),
                )

        # 🔥 6. Sort
        if sort == "oldest":
            query = query.order_by(asc(User.created_at))
        else:
            query = query.order_by(desc(User.created_at))

        # 🔥 7. Total count (AFTER all filters)
        total = query.count()

        # 🔥 8. Paginate (AFTER filters)
        paginated_users = (
            query.offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        # 🔥 9. Get last active for THESE 10 users only
        user_ids = [u.id for u in paginated_users]
        latest_sessions_map = {}
        if user_ids:
            sessions = (
                db.query(
                    UserSession.user_id,
                    func.max(UserSession.created_at).label('last_active')
                )
                .filter(UserSession.user_id.in_(user_ids))
                .group_by(UserSession.user_id)
                .all()
            )
            latest_sessions_map = {s.user_id: s.last_active for s in sessions}

        # 🔥 10. Build results (NO post-filtering!)
        result = []
        for u in paginated_users:
            last_active = _aware(latest_sessions_map.get(u.id))
            is_active = bool(last_active and last_active >= thirty_days_ago)

            result.append(AdminUserItem(
                id=u.id,
                name=u.name,
                email=u.email,
                role=u.role,
                image=u.image,
                is_suspended=u.is_suspended,
                created_at=_aware(u.created_at),
                last_active_at=last_active,
                is_active=is_active,
            ))

        total_pages = max(1, (total + page_size - 1) // page_size)

        return AdminUserListResponse(
            items=result,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    # ==========================================
    # 2. TOGGLE SUSPENSION (same)
    # ==========================================
    @staticmethod
    def toggle_suspension(db: Session, user_id: int) -> User:
        from fastapi import HTTPException
        user = db.query(User).filter(
            User.id == user_id, User.role == "user"
        ).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user.is_suspended = not user.is_suspended
        db.commit()
        db.refresh(user)
        return user

    # ==========================================
    # 3. GET USER DETAILS (same)
    # ==========================================
    @staticmethod
    def get_user_details(db: Session, user_id: int) -> AdminUserDetail:
        user = db.query(User).filter(
            User.id == user_id,
            User.role == "user"
        ).first()

        if not user:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="User not found")

        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)

        latest_session = (
            db.query(UserSession)
            .filter(UserSession.user_id == user_id)
            .order_by(UserSession.created_at.desc())
            .first()
        )
        last_active = _aware(latest_session.created_at) if latest_session else None
        is_active = bool(last_active and last_active >= thirty_days_ago)

        content_count = db.query(func.count(ContentGeneration.id)).filter(
            ContentGeneration.user_id == user_id
        ).scalar() or 0

        campaign_count = db.query(func.count(Campaign.id)).filter(
            Campaign.user_id == user_id
        ).scalar() or 0

        rec_count = db.query(func.count(GrowthRecommendation.id)).filter(
            GrowthRecommendation.user_id == user_id
        ).scalar() or 0

        return AdminUserDetail(
            id=user.id,
            name=user.name,
            email=user.email,
            role=user.role,
            image=user.image,
            is_suspended=user.is_suspended,
            created_at=_aware(user.created_at),
            last_active_at=last_active,
            is_active=is_active,
            total_generations=content_count + campaign_count + rec_count,
            content_generated=content_count,
            campaigns_generated=campaign_count,
            recommendations_generated=rec_count,
        )