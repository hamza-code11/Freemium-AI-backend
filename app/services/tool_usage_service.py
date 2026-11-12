# app/services/tool_usage_service.py

from datetime import datetime, timezone
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.content_generation import ContentGeneration
from app.models.campaign import Campaign
from app.models.growth_recommendation import GrowthRecommendation


# Google Gemini API official free-tier DAILY limits (RPD)
# https://ai.google.dev/gemini-api/docs/rate-limits
GOOGLE_DAILY_LIMITS: dict[str, int] = {
    "content": 500,
    "campaign": 500,
    "growth": 500,
}

TOOL_LABELS: dict[str, str] = {
    "content": "AI Content Generator",
    "campaign": "Campaign Planner",
    "growth": "Growth Recommendations",
}


def _utc_day_bounds() -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start.replace(hour=23, minute=59, second=59, microsecond=999999)
    return start, end


def get_today_tool_usage(db: Session) -> dict[str, int]:
    """Count today's generations per tool from existing tables."""
    start, end = _utc_day_bounds()

    def _count(model) -> int:
        return (
            db.query(func.count(model.id))
            .filter(model.created_at >= start, model.created_at <= end)
            .scalar()
            or 0
        )

    return {
        "content": _count(ContentGeneration),
        "campaign": _count(Campaign),
        "growth": _count(GrowthRecommendation),
    }


def build_tool_usage_payload(db: Session) -> list[dict]:
    used = get_today_tool_usage(db)
    payload: list[dict] = []

    for tool, label in TOOL_LABELS.items():
        limit = GOOGLE_DAILY_LIMITS[tool]
        used_today = used[tool]
        payload.append(
            {
                "tool": tool,
                "label": label,
                "used_today": used_today,
                "daily_limit": limit,
                "remaining": max(0, limit - used_today),
            }
        )

    return payload