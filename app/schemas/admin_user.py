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

    







class AdminBusinessProfile(BaseModel):
    id: int
    business_name: str
    business_type: Optional[str] = None
    business_description: Optional[str] = None
    services: Optional[str] = None
    business_goals: Optional[str] = None
    target_audience: Optional[list[str]] = None
    website: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AdminUserBusinessProfileResponse(BaseModel):
    user_id: int
    user_name: str
    user_email: str
    has_profile: bool
    total_profiles: int = 0 
    profiles: list[AdminBusinessProfile] = [] 
    