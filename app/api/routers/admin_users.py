# app/api/routers/admin_users.py

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.admin_security import get_current_admin
from app.models.admin import Admin
from app.schemas.admin_user import AdminUserListResponse, AdminUserDetail
from app.services.admin_user_service import AdminUserService
from app.schemas.admin_user import AdminUserBusinessProfileResponse

router = APIRouter(prefix="/api/admin/users", tags=["Admin Users"])


@router.get("", response_model=AdminUserListResponse)
def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    search: Optional[str] = Query(None),
    status: str = Query("all", description="all | active | inactive | suspended"),
    sort: str = Query("latest", description="latest | oldest"),
    date_range: str = Query("all", description="all | today | week | month | year | custom"),
    custom_from: Optional[datetime] = Query(None),
    custom_to: Optional[datetime] = Query(None),
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return AdminUserService.list_users(
        db,
        page=page,
        page_size=page_size,
        search=search,
        status=status,
        sort=sort,
        date_range=date_range,
        custom_from=custom_from,
        custom_to=custom_to,
    )


@router.get("/{user_id}", response_model=AdminUserDetail)
def get_user_details(
    user_id: int,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return AdminUserService.get_user_details(db, user_id)


@router.patch("/{user_id}/toggle-suspension")
def toggle_user_suspension(
    user_id: int,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    user = AdminUserService.toggle_suspension(db, user_id)
    return {
        "message": "User suspended" if user.is_suspended else "User activated",
        "is_suspended": user.is_suspended,
    }



@router.get("/{user_id}/business-profile", response_model=AdminUserBusinessProfileResponse)
def get_user_business_profile(
    user_id: int,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return AdminUserService.get_business_profile(db, user_id)

