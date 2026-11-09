from fastapi import (
    APIRouter, BackgroundTasks, Depends, Request,
    UploadFile, File, Form
)
from sqlalchemy.orm import Session

from app.core.admin_security import get_current_admin
from app.core.database import get_db
from app.core.limiter import limiter
from app.models.admin import Admin
from app.schemas.admin import (
    AdminLogin, AdminForgotPassword, AdminResetPassword,
    AdminChangePassword, AdminResponse
)
from app.services.admin_service import AdminService

router = APIRouter(prefix="/api/admin", tags=["Admin Auth"])


@router.post("/login")
@limiter.limit("5/minute")
def admin_login(
    request: Request,
    data: AdminLogin,
    db: Session = Depends(get_db)
):
    return AdminService.login(db, data.email, data.password)


@router.post("/forgot-password")
@limiter.limit("3/minute")
def admin_forgot_password(
    request: Request,
    data: AdminForgotPassword,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    return AdminService.forgot_password(db, data.email, background_tasks)


@router.post("/reset-password")
@limiter.limit("10/minute")
def admin_reset_password(
    request: Request,
    data: AdminResetPassword,
    db: Session = Depends(get_db)
):
    return AdminService.reset_password(db, data.email, data.otp, data.new_password)


@router.post("/change-password")
def admin_change_password(
    data: AdminChangePassword,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    return AdminService.change_password(
        db, admin, data.current_password, data.new_password
    )


@router.patch("/profile", response_model=AdminResponse)
async def admin_update_profile(
    name: str | None = Form(default=None, min_length=2, max_length=100),
    image: UploadFile | None = File(default=None),
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    return await AdminService.update_profile(db, admin, name, image)



@router.get("/me", response_model=AdminResponse)
def get_current_admin_data(
    admin: Admin = Depends(get_current_admin)
):
    return admin