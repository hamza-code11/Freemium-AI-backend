# app/services/support_ticket_service.py

from uuid import uuid4
from pathlib import Path
from datetime import datetime, timezone

from fastapi import HTTPException, status, UploadFile
from sqlalchemy.orm import Session

from app.models.support_ticket import SupportTicket
from app.repositories.support_ticket_repository import SupportTicketRepository
from app.schemas.support_ticket import SupportTicketCreate, SupportTicketListResponse, SupportTicketResponse


class SupportTicketService:

    # ==========================================
    # 1. CREATE TICKET
    # ==========================================
    @staticmethod
    def create_ticket(
        db: Session,
        user_id: int,
        data: SupportTicketCreate,
        attachment: UploadFile | None = None,
    ) -> SupportTicket:
        
        # Handle file upload
        attachment_filename = None
        if attachment and attachment.filename:
            attachment_filename = SupportTicketService._save_attachment(attachment)

        # Generate ticket number
        ticket_number = SupportTicketRepository.generate_ticket_number(db)

        # Create record
        try:
            ticket = SupportTicketRepository.create(db, {
                "ticket_number": ticket_number,
                "user_id": user_id,
                "name": data.name,
                "email": data.email.lower(),
                "subject": data.subject,
                "description": data.description,
                "attachment": attachment_filename,
                "status": "Pending",  # 🔥 Default status
            })
            return ticket
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create ticket: {str(e)}",
            )

    # ==========================================
    # 2. LIST USER TICKETS (Paginated)
    # ==========================================
    @staticmethod
    def list_user_tickets(
        db: Session,
        user_id: int,
        page: int = 1,
        page_size: int = 5,
    ) -> SupportTicketListResponse:
        
        items, total = SupportTicketRepository.get_by_user_paginated(
            db, user_id, page=page, page_size=page_size
        )

        total_pages = max(1, (total + page_size - 1) // page_size)

        return SupportTicketListResponse(
            items=[SupportTicketResponse.model_validate(t) for t in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    # ==========================================
    # HELPER: Save File
    # ==========================================
    @staticmethod
    def _save_attachment(file: UploadFile) -> str:
        MAX_SIZE = 5 * 1024 * 1024  # 5MB
        ALLOWED = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
            "application/pdf": ".pdf",
            "application/msword": ".doc",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
        }

        if file.content_type not in ALLOWED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file type. Allowed: JPG, PNG, WEBP, PDF, DOC, DOCX",
            )

        # Read file
        content = file.file.read(MAX_SIZE + 1)

        if len(content) > MAX_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File size must not exceed 5MB",
            )

        # Generate filename
        ext = ALLOWED[file.content_type]
        filename = f"{uuid4().hex}{ext}"

        # Save to uploads/support/
        upload_dir = Path(__file__).resolve().parents[2] / "uploads" / "support"
        upload_dir.mkdir(parents=True, exist_ok=True)
        (upload_dir / filename).write_bytes(content)

        return filename

    