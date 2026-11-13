from typing import Optional
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.admin_security import get_current_admin
from app.models.admin import Admin
from app.schemas.contact_message import (
    ContactMessageCreate,
    ContactMessageListItem,
    ContactMessageListResponse,
    ContactSubmitResponse,
)
from app.services.contact_message_service import ContactMessageService

router = APIRouter(prefix="/api/contact", tags=["Contact"])
admin_router = APIRouter(prefix="/api/admin/contact", tags=["Admin Contact"])


# ============================================================
# PUBLIC — submit form
# ============================================================
@router.post("", response_model=ContactSubmitResponse)
def submit_contact_form(
    payload: ContactMessageCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    saved = ContactMessageService.create(db, payload, request)
    return ContactSubmitResponse(
        success=True,
        message="Thanks! We've received your message and will respond soon.",
        id=saved.id,
    )


# ============================================================
# ADMIN — list (paginated)
# ============================================================
@admin_router.get("", response_model=ContactMessageListResponse)
def list_messages(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(
        10, ge=1, le=100, description="Items per page (max 100)"
    ),
    search: Optional[str] = Query(None, description="Search in name/email/subject"),
    unread_only: bool = Query(False, description="Show only unread messages"),
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return ContactMessageService.list(
        db,
        page=page,
        page_size=page_size,
        search=search,
        unread_only=unread_only,
    )


# ============================================================
# ADMIN — single message
# ============================================================
@admin_router.get("/{message_id}", response_model=ContactMessageListItem)
def get_message(
    message_id: int,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return ContactMessageService.get(db, message_id)


# ============================================================
# ADMIN — mark read / unread
# ============================================================
@admin_router.patch("/{message_id}/read", response_model=ContactMessageListItem)
def mark_read(
    message_id: int,
    read: bool = Query(True, description="true = mark read, false = mark unread"),
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return ContactMessageService.mark_read(db, message_id, read=read)


# ============================================================
# ADMIN — delete
# ============================================================
@admin_router.delete("/{message_id}")
def delete_message(
    message_id: int,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    ContactMessageService.delete(db, message_id)
    return {"success": True}

