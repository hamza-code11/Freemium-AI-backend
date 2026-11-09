# app/schemas/dashboard.py

from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, ConfigDict


class DashboardStats(BaseModel):
    total_generations: int
    content_generated: int
    campaigns_generated: int
    recommendations_generated: int


class DashboardHistoryItem(BaseModel):
    id: int
    type: str
    title: str
    preview: str
    content: Optional[str] = None
    created_at: datetime
    metadata: dict[str, Any] = {}

    model_config = ConfigDict(from_attributes=True)


#  Chart Data
class UsageChartData(BaseModel):
    labels: list[str]
    values: list[int]


class BreakdownItem(BaseModel):
    label: str
    value: int
    color: str


class DashboardResponse(BaseModel):
    stats: DashboardStats
    recent_content: list[DashboardHistoryItem]
    recent_campaigns: list[DashboardHistoryItem]
    recent_recommendations: list[DashboardHistoryItem]
    
    #  Charts
    usage_chart: UsageChartData
    breakdown: list[BreakdownItem]