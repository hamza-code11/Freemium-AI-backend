# app/schemas/history.py

from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, ConfigDict


class HistoryItem(BaseModel):
    id: int
    type: str  # "content" | "campaign" | "recommendation"
    title: str
    preview: str
    content: Optional[str] = None
    created_at: datetime
    metadata: dict[str, Any] = {}

    model_config = ConfigDict(from_attributes=True)


class HistoryResponse(BaseModel):
    items: list[HistoryItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class HistoryStats(BaseModel):
    total_generations: int
    content_generated: int
    campaigns_generated: int
    recommendations_generated: int