# app/repositories/support_ticket_repository.py

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.support_ticket import SupportTicket


class SupportTicketRepository:

    @staticmethod
    def create(db: Session, data: dict) -> SupportTicket:
        ticket = SupportTicket(**data)
        db.add(ticket)
        db.commit()
        db.refresh(ticket)
        return ticket

    @staticmethod
    def get_by_user_paginated(
        db: Session,
        user_id: int,
        page: int = 1,
        page_size: int = 5,
    ):
        query = (
            db.query(SupportTicket)
            .filter(SupportTicket.user_id == user_id)
            .order_by(SupportTicket.created_at.desc())
        )

        total = query.count()
        offset = (page - 1) * page_size
        items = query.offset(offset).limit(page_size).all()

        return items, total

    @staticmethod
    def generate_ticket_number(db: Session) -> str:
        """Generate sequential ticket number like TKT-1043."""
        # Count all tickets + 1000 as base
        count = db.query(func.count(SupportTicket.id)).scalar() or 0
        return f"TKT-{1000 + count + 1}"

    @staticmethod
    def get_by_id(db: Session, ticket_id: int):
        return db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
    