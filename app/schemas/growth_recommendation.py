# app/schemas/growth_recommendation.py

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict


class GrowthRecommendationRequest(BaseModel):
    business_id: Optional[int] = Field(default=None, description="Selected business profile ID")
    business_goals: Optional[str] = Field(default=None, max_length=2000)
    challenges: Optional[str] = Field(default=None, max_length=2000)
    target_audience: List[str] = Field(default_factory=list, max_length=20)
    ai_instruction: Optional[str] = Field(default=None, max_length=1000)


class RecommendationItem(BaseModel):
    title: str
    desc: str
    bullets: List[str] = []
    benefit: str = ""
    why: str = ""
    checklist: List[str] = []
    tools: List[str] = []
    metrics: List[str] = []

    model_config = ConfigDict(extra="ignore")


class GrowthRecommendationResponse(BaseModel):
    id: int
    recommendations: List[RecommendationItem]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
    