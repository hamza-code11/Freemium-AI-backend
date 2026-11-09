# app/api/routers/dashboard.py

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.core.security import verify_access_token
from app.schemas.dashboard import DashboardResponse
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardResponse)
def get_dashboard_data(
    user_id: int = Depends(verify_access_token),
    db: Session = Depends(get_db),
    range: str = Query("week", description="today | week | month | year | all | custom"),
    custom_from: Optional[datetime] = Query(None),
    custom_to: Optional[datetime] = Query(None),
):
    """
    Single API call that returns dashboard data.
    `range` parameter controls the usage chart & breakdown data.
    """
    return DashboardService.get_dashboard(
        db=db,
        user_id=user_id,
        range_type=range,
        custom_from=custom_from,
        custom_to=custom_to,
    )