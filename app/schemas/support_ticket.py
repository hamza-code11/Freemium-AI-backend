# app/schemas/support_ticket.py

from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, EmailStr, Field, ConfigDict


TicketStatus = Literal["Pending", "In Progress", "Resolved"]


class SupportTicketCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    subject: str = Field(..., min_length=3, max_length=255)
    description: str = Field(..., min_length=10, max_length=5000)


class SupportTicketResponse(BaseModel):
    id: int
    ticket_number: str
    name: str
    email: EmailStr
    subject: str
    description: str
    attachment: Optional[str] = None
    status: TicketStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SupportTicketListResponse(BaseModel):
    items: list[SupportTicketResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class SupportTicketStatusUpdate(BaseModel):
    status: TicketStatus