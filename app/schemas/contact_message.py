from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class ContactMessageCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    email: EmailStr
    subject: str = Field(..., min_length=3, max_length=200)
    message: str = Field(..., min_length=10, max_length=5000)


class ContactMessageResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    subject: str
    message: str
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ContactMessageListItem(BaseModel):
    id: int
    name: str
    email: EmailStr
    subject: str
    message: str
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ContactMessageListResponse(BaseModel):
    items: list[ContactMessageListItem]
    total: int
    page: int
    page_size: int
    total_pages: int
    unread: int


class ContactSubmitResponse(BaseModel):
    success: bool
    message: str
    id: int