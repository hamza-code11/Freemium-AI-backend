from datetime import datetime
from typing import Any, Literal, Optional
from pydantic import BaseModel, EmailStr


class UsageRecordItem(BaseModel):
    id: int
    user_id: int
    user_name: str
    user_email: EmailStr
    user_image: Optional[str] = None
    feature: Literal["content", "campaign", "growth"]
    title: str
    status: Literal["success", "failed"]
    created_at: datetime


class UsageRecordListResponse(BaseModel):
    items: list[UsageRecordItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class UsageRecordDetail(BaseModel):
    id: int
    user_id: int
    user_name: str
    user_email: EmailStr
    user_image: Optional[str] = None
    feature: Literal["content", "campaign", "growth"]
    title: str
    status: Literal["success", "failed"]
    created_at: datetime
    input_payload: dict[str, Any]
    output_payload: Any


class UsageStatsResponse(BaseModel):
    total_generations: int
    content_generations: int
    campaign_generations: int
    growth_generations: int


class UsageChartPoint(BaseModel):
    date: str
    content: int
    campaign: int
    growth: int
    failed: int


class UsageChartResponse(BaseModel):
    points: list[UsageChartPoint]
    totals: dict[str, int]