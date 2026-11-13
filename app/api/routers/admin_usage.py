from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.admin_security import get_current_admin
from app.models.admin import Admin
from app.schemas.admin_usage import (
    UsageRecordListResponse,
    UsageRecordDetail,
    UsageStatsResponse,
    UsageChartResponse,
)
from app.services.admin_usage_service import AdminUsageService

router = APIRouter(prefix="/api/admin/usage", tags=["Admin Usage"])


@router.get("/stats", response_model=UsageStatsResponse)
def usage_stats(
    date_range: str = Query("all"),
    feature: Optional[str] = Query(None),
    custom_from: Optional[datetime] = Query(None),
    custom_to: Optional[datetime] = Query(None),
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return AdminUsageService.get_stats(
        db, date_range=date_range, custom_from=custom_from,
        custom_to=custom_to, feature=feature,
    )


@router.get("/chart", response_model=UsageChartResponse)
def usage_chart(
    date_range: str = Query("all"),
    feature: Optional[str] = Query(None),
    custom_from: Optional[datetime] = Query(None),
    custom_to: Optional[datetime] = Query(None),
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return AdminUsageService.get_chart(
        db, date_range=date_range, custom_from=custom_from,
        custom_to=custom_to, feature=feature,
    )


@router.get("/detail/{feature}/{record_id}", response_model=UsageRecordDetail)
def usage_detail(
    feature: str,
    record_id: int,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return AdminUsageService.get_detail(db, feature, record_id)


@router.get("", response_model=UsageRecordListResponse)
def list_usage(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    search: Optional[str] = Query(None),
    sort: str = Query("latest"),
    date_range: str = Query("all"),
    feature: Optional[str] = Query(None),
    custom_from: Optional[datetime] = Query(None),
    custom_to: Optional[datetime] = Query(None),
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return AdminUsageService.list_records(
        db, page=page, page_size=page_size, search=search, sort=sort,
        date_range=date_range, custom_from=custom_from, custom_to=custom_to,
        feature=feature,
    )

