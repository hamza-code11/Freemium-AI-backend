# app/api/routers/admin_stats.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.admin_security import get_current_admin
from app.models.admin import Admin
from app.schemas.admin_stats import AdminUserStats
from app.services.admin_stats_service import AdminStatsService

router = APIRouter(prefix="/api/admin/stats", tags=["Admin Stats"])


@router.get("/users", response_model=AdminUserStats)
def get_user_stats(
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Get user stats for admin dashboard:
    - Total users
    - Active users (last 30 days)
    - Inactive users
    - Suspended users
    """
    return AdminStatsService.get_user_stats(db)
