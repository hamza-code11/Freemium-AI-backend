# app/api/routers/admin_dashboard.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.admin_security import get_current_admin
from app.models.admin import Admin
from app.schemas.admin_dashboard import AdminDashboardResponse
from app.services.admin_dashboard_service import AdminDashboardService

router = APIRouter(prefix="/api/admin/dashboard", tags=["Admin Dashboard"])


@router.get("", response_model=AdminDashboardResponse)
def get_dashboard(
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return AdminDashboardService.get_dashboard(db)
