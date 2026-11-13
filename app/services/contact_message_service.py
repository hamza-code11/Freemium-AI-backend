from typing import Optional

from fastapi import HTTPException, Request
from sqlalchemy import func, desc, text
from sqlalchemy.orm import Session

from app.models.contact_message import ContactMessage
from app.schemas.contact_message import (
    ContactMessageCreate,
    ContactMessageResponse,
    ContactMessageListResponse,
    ContactMessageListItem,
)


class ContactMessageService:

    @staticmethod
    def create(
        db: Session,
        payload: ContactMessageCreate,
        request: Optional[Request] = None,
    ) -> ContactMessageResponse:
        ip = None
        ua = None
        if request is not None:
            ip = request.client.host if request.client else None
            ua = request.headers.get("user-agent")
            if ua and len(ua) > 500:
                ua = ua[:500]

        msg = ContactMessage(
            name=payload.name.strip(),
            email=str(payload.email).lower().strip(),
            subject=payload.subject.strip(),
            message=payload.message.strip(),
            ip_address=ip,
            user_agent=ua,
            is_read=0,
        )
        db.add(msg)
        db.commit()
        db.refresh(msg)

        return ContactMessageResponse.model_validate(msg)

    # ------------------------------------------------------------------
    # LIST — Highly Optimized
    # ------------------------------------------------------------------

    @staticmethod
    def list(
        db: Session,
        page: int = 1,
        page_size: int = 10,
        search: Optional[str] = None,
        unread_only: bool = False,
    ) -> ContactMessageListResponse:
        
        q = db.query(ContactMessage)

        # 1. SMART SEARCH (Full-Text + Fallback for Emails)
        if search and search.strip():
            term = search.strip()
            
            # Agar search mein '@' ya '.' hai (yani email hai), toh LIKE query chalayein
            # Kyunki MATCH AGAINST email symbols (@, .) ke sath properly kaam nahi karta
            if "@" in term or "." in term:
                like_term = f"%{term}%"
                q = q.filter(ContactMessage.email.ilike(like_term))
            else:
                try:
                    # Normal Naam ya Subject ke liye FAST Full-Text search
                    q = q.filter(
                        text("MATCH(contact_messages.name, contact_messages.email, contact_messages.subject) AGAINST(:term IN BOOLEAN MODE)")
                    ).params(term=f"{term}*")
                    q.count() # Test karo agar index mojood hai
                except Exception:
                    # Agar index nahi bana (fallback), toh LIKE query chalayein
                    db.rollback()
                    q = db.query(ContactMessage)
                    like_term = f"%{term}%"
                    q = q.filter(
                        (ContactMessage.name.ilike(like_term)) | 
                        (ContactMessage.email.ilike(like_term)) | 
                        (ContactMessage.subject.ilike(like_term))
                    )

        # 2. UNREAD FILTER
        if unread_only:
            q = q.filter(ContactMessage.is_read == 0)

        # 3. FAST TOTAL COUNT 
        if not search and not unread_only:
            total = db.execute(text("SELECT COUNT(id) FROM contact_messages")).scalar() or 0
        else:
            total = q.count()

        # 4. GLOBAL UNREAD COUNT 
        unread_total = (
            db.query(func.count(ContactMessage.id))
            .filter(ContactMessage.is_read == 0)
            .scalar()
            or 0
        )

        # 5. PAGINATION
        rows = (
            q.order_by(desc(ContactMessage.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        items = [
            ContactMessageListItem(
                id=r.id,
                name=r.name,
                email=r.email,
                subject=r.subject,
                message=r.message,
                is_read=bool(r.is_read),
                created_at=r.created_at,
            )
            for r in rows
        ]

        total_pages = max(1, (total + page_size - 1) // page_size)

        return ContactMessageListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            unread=unread_total,
        )

    

    # ------------------------------------------------------------------
    # GET single
    # ------------------------------------------------------------------
    @staticmethod
    def get(db: Session, message_id: int) -> ContactMessageListItem:
        row = db.query(ContactMessage).filter(ContactMessage.id == message_id).first()
        if not row:
            raise HTTPException(status_code=404, detail="Message not found")
        return ContactMessageListItem(
            id=row.id,
            name=row.name,
            email=row.email,
            subject=row.subject,
            message=row.message,
            is_read=bool(row.is_read),
            created_at=row.created_at,
        )

    # ------------------------------------------------------------------
    # MARK READ / UNREAD
    # ------------------------------------------------------------------
    @staticmethod
    def mark_read(
        db: Session, message_id: int, read: bool = True
    ) -> ContactMessageListItem:
        row = db.query(ContactMessage).filter(ContactMessage.id == message_id).first()
        if not row:
            raise HTTPException(status_code=404, detail="Message not found")
        row.is_read = 1 if read else 0
        db.commit()
        db.refresh(row)
        return ContactMessageListItem(
            id=row.id,
            name=row.name,
            email=row.email,
            subject=row.subject,
            message=row.message,
            is_read=bool(row.is_read),
            created_at=row.created_at,
        )

    # ------------------------------------------------------------------
    # DELETE
    # ------------------------------------------------------------------
    @staticmethod
    def delete(db: Session, message_id: int) -> None:
        row = db.query(ContactMessage).filter(ContactMessage.id == message_id).first()
        if not row:
            raise HTTPException(status_code=404, detail="Message not found")
        db.delete(row)
        db.commit()

        