from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    Request,
    Response,
    Cookie,
    HTTPException,
    status,
    UploadFile,
    File,
    Form
)
from app.core.limiter import limiter
from sqlalchemy.orm import Session
from app.core.security import verify_access_token

from app.core.config import (
    COOKIE_SECURE,
    REFRESH_TOKEN_EXPIRE_DAYS,
)
from app.core.database import get_db
from app.schemas.user import UserCreate, UserResponse, UserLogin, ChangePassword, ForgotPasswordRequest, VerifyPasswordResetOTP, ResetPassword
from app.services.user_service import UserService
from app.repositories.user_repository import UserRepository
from app.services.password_reset_service import PasswordResetService

router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"]
)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED
)
def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    return UserService.register_user(
        db,
        user_data.model_dump()
    )



@router.post("/login")
@limiter.limit("5/minute")
def login(
    request: Request,
    response: Response,
    user_data: UserLogin,
    db: Session = Depends(get_db)
):
    result = UserService.login_user(
        db,
        user_data.email,
        user_data.password
    )

    response.set_cookie(
        key="refresh_token",
        value=result["refresh_token"],
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/api/auth"
    )

    # USER DATA BHI RETURN KAREIN
    return {
        "access_token": result["access_token"],
        "token_type": "bearer",
        "user": UserResponse.model_validate(result["user"]) # User data add kiya
    }



@router.get("/me", response_model=UserResponse)
def get_current_user(
    user_id: int = Depends(verify_access_token),
    db: Session = Depends(get_db)
):
    # 🔥 Ab ye joinedload ke sath user aur business_profiles dono layega
    user = UserRepository.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user




@router.post("/refresh")
def refresh(
    response: Response,
    db: Session = Depends(get_db),
    refresh_token: str | None = Cookie(default=None)
):
    if not refresh_token:
        raise HTTPException(
            status_code=401,
            detail="Refresh token missing"
        )

    result = UserService.refresh_access_token(
        db,
        refresh_token
    )

    response.set_cookie(
        key="refresh_token",
        value=result["refresh_token"],
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/api/auth"
    )

    return {
        "access_token": result["access_token"],
        "token_type": "bearer"
    }



@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    db: Session = Depends(get_db),
    refresh_token: str | None = Cookie(default=None)
):
    try:
        UserService.logout_user(db, refresh_token)
    finally:
        response.delete_cookie(
            key="refresh_token",
            path="/api/auth",
            httponly=True,
            secure=COOKIE_SECURE,
            samesite="lax"
        )

    return None



@router.post("/logout-all")
def logout_all_devices(
    response: Response,
    user_id: int = Depends(verify_access_token),
    db: Session = Depends(get_db)
):
    revoked_count = UserService.logout_all_devices(
        db=db,
        user_id=user_id
    )

    response.delete_cookie(
        key="refresh_token",
        path="/api/auth",
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax"
    )

    return {
        "message": "Logged out from all devices successfully",
        "revoked_sessions": revoked_count
    }



@router.patch("/profile", response_model=UserResponse)
async def update_profile(
    name: str | None = Form(default=None, min_length=2, max_length=100),
    image: UploadFile | None = File(default=None),
    user_id: int = Depends(verify_access_token),
    db: Session = Depends(get_db)
):
    user = UserRepository.get_by_id(db, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    updated_user = await UserService.update_profile(
        db=db,
        user=user,
        name=name,
        image=image
    )

    return updated_user




@router.post("/change-password")
def change_password(
    password_data: ChangePassword,
    response: Response,
    user_id: int = Depends(verify_access_token),
    db: Session = Depends(get_db)
):
    user = UserRepository.get_by_id(db, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    result = UserService.change_password(
        db=db,
        user=user,
        current_password=password_data.current_password,
        new_password=password_data.new_password
    )

    response.delete_cookie(
        key="refresh_token",
        path="/api/auth",
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax"
    )

    return result




@router.post("/forgot-password")
@limiter.limit("3/minute")
def forgot_password(
    request: Request,
    background_tasks: BackgroundTasks,
    payload: ForgotPasswordRequest,
    db: Session = Depends(get_db)
):
    return PasswordResetService.request_password_reset(
        db=db,
        email=payload.email,
        background_tasks=background_tasks
    )


@router.post("/verify-reset-otp")
@limiter.limit("10/minute")
def verify_reset_otp(
    request: Request,
    payload: VerifyPasswordResetOTP,
    db: Session = Depends(get_db)
):
    return PasswordResetService.verify_reset_otp(
        db=db,
        email=payload.email,
        otp=payload.otp
    )




@router.post("/reset-password")
def reset_password(
    request: ResetPassword,
    db: Session = Depends(get_db)
):
    return PasswordResetService.reset_password(
        db=db,
        reset_token=request.reset_token,
        new_password=request.new_password
    )


