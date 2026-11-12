# app/schemas/admin_user.py

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict


class AdminUserItem(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str
    image: Optional[str] = None
    is_suspended: bool
    created_at: datetime
    last_active_at: Optional[datetime] = None  # From session table
    is_active: bool  # Computed: last_active within 30 days

    model_config = ConfigDict(from_attributes=True)


class AdminUserListResponse(BaseModel):
    items: list[AdminUserItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class AdminUserDetail(AdminUserItem):
    # Extra info for details panel
    total_generations: int = 0
    content_generated: int = 0
    campaigns_generated: int = 0
    recommendations_generated: int = 0
    