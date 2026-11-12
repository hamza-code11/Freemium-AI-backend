# app/schemas/admin_dashboard.py

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, ConfigDict


class DashboardUserStats(BaseModel):
    total_users: int
    active_users: int
    inactive_users: int
    content_generations: int
    campaign_generations: int
    growth_generations: int


class ToolUsageItem(BaseModel):
    tool: Literal["content", "campaign", "growth"]
    label: str
    used_today: int
    daily_limit: int
    remaining: int


class RecentGenerationItem(BaseModel):
    id: int
    user_id: int
    user_name: str
    user_email: EmailStr
    generation_type: Literal["content", "campaign", "growth"]
    title: str
    created_at: datetime


class RecentLoginItem(BaseModel):
    id: int
    name: str
    email: EmailStr
    image: Optional[str] = None
    logged_in_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminDashboardResponse(BaseModel):
    stats: DashboardUserStats
    tool_usage: list[ToolUsageItem]
    recent_generations: list[RecentGenerationItem]
    recent_logins: list[RecentLoginItem]