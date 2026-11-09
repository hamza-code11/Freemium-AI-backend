# app/api/routers/support.py

from fastapi import APIRouter, Depends, status, UploadFile, File, Form, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_access_token
from app.schemas.support_ticket import (
    SupportTicketCreate,
    SupportTicketResponse,
    SupportTicketListResponse,
)
from app.services.support_ticket_service import SupportTicketService

router = APIRouter(prefix="/api/support", tags=["Support Tickets"])


# ==========================================
# 1. CREATE TICKET
# ==========================================
@router.post(
    "/tickets",
    response_model=SupportTicketResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_support_ticket(
    name: str = Form(..., min_length=2, max_length=100),
    email: str = Form(..., min_length=5, max_length=255),
    subject: str = Form(..., min_length=3, max_length=255),
    description: str = Form(..., min_length=10, max_length=5000),
    attachment: UploadFile | None = File(default=None),
    user_id: int = Depends(verify_access_token),
    db: Session = Depends(get_db),
):
    """
    Submit a support ticket. Attachment is optional.
    Status is set to 'Pending' by default.
    """
    data = SupportTicketCreate(
        name=name,
        email=email,
        subject=subject,
        description=description,
    )

    return SupportTicketService.create_ticket(
        db=db,
        user_id=user_id,
        data=data,
        attachment=attachment,
    )


# ==========================================
# 2. LIST USER TICKETS (Paginated)
# ==========================================
@router.get(
    "/tickets",
    response_model=SupportTicketListResponse,
)
def list_user_tickets(
    page: int = Query(1, ge=1),
    page_size: int = Query(5, ge=1, le=50),
    user_id: int = Depends(verify_access_token),
    db: Session = Depends(get_db),
):
    """
    List all support tickets for the current user (paginated).
    """
    return SupportTicketService.list_user_tickets(
        db=db,
        user_id=user_id,
        page=page,
        page_size=page_size,
    )
