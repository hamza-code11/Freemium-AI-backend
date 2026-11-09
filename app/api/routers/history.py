# app/api/routers/history.py

from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_access_token
from app.schemas.history import HistoryResponse, HistoryStats
from app.services.history_service import HistoryService

router = APIRouter(prefix="/api/history", tags=["History"])


@router.get("/stats", response_model=HistoryStats)
def get_history_stats(
    user_id: int = Depends(verify_access_token),
    db: Session = Depends(get_db),
):
    """Get user's generation counts."""
    return HistoryService.get_stats(db, user_id)


@router.get("", response_model=HistoryResponse)
def get_history(
    user_id: int = Depends(verify_access_token),
    db: Session = Depends(get_db),
    type_filter: str = Query("all"),
    date_range: str = Query("all"),
    custom_from: datetime | None = Query(None),
    custom_to: datetime | None = Query(None),
    sort: str = Query("latest"),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
):
    """Get user's full history with filters & pagination."""
    return HistoryService.get_history(
        db=db,
        user_id=user_id,
        type_filter=type_filter,
        date_range=date_range,
        custom_from=custom_from,
        custom_to=custom_to,
        sort=sort,
        search=search,
        page=page,
        page_size=page_size,
    )