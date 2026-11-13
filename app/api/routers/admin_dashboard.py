from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.admin_security import get_current_admin
from app.models.admin import Admin
from app.schemas.admin_dashboard import AdminDashboardResponse
from app.services.admin_dashboard_service import AdminDashboardService

router = APIRouter(prefix="/api/admin/dashboard", tags=["Admin Dashboard"])


@router.get("", response_model=AdminDashboardResponse)
def get_dashboard(
    date_range: str = Query("all", description="all | today | week | month | year | custom"),
    custom_from: Optional[datetime] = Query(None),
    custom_to: Optional[datetime] = Query(None),
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return AdminDashboardService.get_dashboard(
        db,
        date_range=date_range,
        custom_from=custom_from,
        custom_to=custom_to,
    )