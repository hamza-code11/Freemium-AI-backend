# app/services/growth_recommendation_service.py

import json
import re
from typing import Any

from fastapi import HTTPException, status
from google import genai
from sqlalchemy.orm import Session

from app.core.config import GEMINI_RECOMMENDATION_API_KEY
from app.models.business_profile import BusinessProfile
from app.models.growth_recommendation import GrowthRecommendation
from app.schemas.growth_recommendation import GrowthRecommendationRequest

client = genai.Client(api_key=GEMINI_RECOMMENDATION_API_KEY)

ALLOWED_TOOLS = {
    "instagram", "facebook", "tiktok", "later",
    "canva", "mailchimp", "analytics", "website",
}


class GrowthRecommendationService:

    # ============================================
    # HELPERS
    # ============================================

    @staticmethod
    def _clean_json_text(text: str) -> str:
        """Remove markdown code fences from AI output."""
        text = text.strip()
        text = re.sub(r"^```json\s*", "", text)
        text = re.sub(r"^```\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        return text.strip()

    @staticmethod
    def _sanitize_recommendations(recs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Clean each recommendation: filter tools, ensure strings, ensure lists."""
        cleaned = []
        for rec in recs:
            if not isinstance(rec, dict):
                continue

            tools = [
                t for t in (rec.get("tools") or [])
                if isinstance(t, str) and t.lower() in ALLOWED_TOOLS
            ]

            cleaned.append({
                "title": str(rec.get("title") or "Untitled Recommendation"),
                "desc": str(rec.get("desc") or ""),
                "bullets": [str(b) for b in (rec.get("bullets") or []) if b],
                "benefit": str(rec.get("benefit") or ""),
                "why": str(rec.get("why") or ""),
                "checklist": [str(c) for c in (rec.get("checklist") or []) if c],
                "tools": tools,
                "metrics": [str(m) for m in (rec.get("metrics") or []) if m],
            })

        return cleaned

    # ============================================
    # MAIN METHOD
    # ============================================

    @staticmethod
    def generate_recommendations(
        db: Session,
        user_id: int,
        payload: GrowthRecommendationRequest,
    ) -> dict:

        # --- 1. Fetch Business Profile ---
        business = None
        if payload.business_id:
            business = (
                db.query(BusinessProfile)
                .filter(
                    BusinessProfile.id == payload.business_id,
                    BusinessProfile.user_id == user_id,
                )
                .first()
            )

        biz_name = business.business_name if business else "N/A"
        biz_type = business.business_type if business else "N/A"
        biz_desc = business.business_description if business else "N/A"
        biz_services = business.services if business else "N/A"

        # --- 2. Merge user input with business defaults ---
        goals = payload.business_goals or (
            business.business_goals if business else None
        ) or "Not specified"
        audience_str = ", ".join(payload.target_audience) if payload.target_audience else "General Audience"
        challenges_str = payload.challenges or "Not specified"
        instruction_str = payload.ai_instruction or "None"

        # --- 3. Build Prompt ---
        prompt = f"""
        You are an expert business growth strategist and AI marketing consultant.
        Generate 3 to 5 highly actionable growth recommendations tailored to the following business.

        ### Business Context:
        - Business Name: {biz_name}
        - Business Type: {biz_type}
        - Services / Products: {biz_services}
        - Business Description: {biz_desc}
        - Business Goals: {goals}
        - Target Audience: {audience_str}
        - Current Challenges: {challenges_str}
        - Special AI Instructions: {instruction_str}

        ### Required Output Format (Valid JSON only, no markdown):
        {{
            "recommendations": [
                {{
                    "title": "Actionable recommendation title",
                    "desc": "1-2 sentence summary",
                    "bullets": ["Action step 1", "Action step 2"],
                    "benefit": "Expected outcome",
                    "why": "Why this matters for this specific business",
                    "checklist": ["Task 1", "Task 2"],
                    "tools": ["instagram", "facebook"],
                    "metrics": ["KPI 1", "KPI 2"]
                }}
            ]
        }}

        IMPORTANT:
        1. Respond with VALID JSON only. No markdown code blocks or extra text.
        2. Generate 3 to 5 recommendations.
        3. 'tools' field must use only these values: instagram, facebook, tiktok, later, canva, mailchimp, analytics, website.
        4. Recommendations must be specific to the business goals and challenges, not generic.
        5. Use the 'Services / Products' field to suggest product-focused recommendations.
        """

        # --- 4. AI Call ---
        try:
            response = client.models.generate_content(
                model="gemini-3.1-flash-lite",
                contents=prompt,
            )
        except Exception as e:
            print(f"[GrowthRec] AI call failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="AI service is unavailable. Please try again later.",
            )

        if not response or not response.text:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="AI returned an empty response.",
            )

        # --- 5. Parse JSON ---
        try:
            clean = GrowthRecommendationService._clean_json_text(response.text)
            parsed = json.loads(clean)
        except json.JSONDecodeError as e:
            print(f"[GrowthRec] JSON parse failed: {e}\nRaw: {response.text[:500]}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="AI returned invalid format. Please try again.",
            )

        recs_raw = parsed.get("recommendations", [])
        if not recs_raw or not isinstance(recs_raw, list):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="AI returned no recommendations.",
            )

        # --- 6. Sanitize ---
        recommendations = GrowthRecommendationService._sanitize_recommendations(recs_raw)
        if not recommendations:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="AI returned no valid recommendations.",
            )

        # --- 7. Save to DB ---
        try:
            record = GrowthRecommendation(
                user_id=user_id,
                business_id=payload.business_id,
                business_goals=goals,
                challenges=payload.challenges,
                target_audience=payload.target_audience or [],
                ai_instruction=payload.ai_instruction,
                recommendations=recommendations,
            )
            db.add(record)
            db.commit()
            db.refresh(record)
        except Exception as e:
            db.rollback()
            print(f"[GrowthRec] DB save failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save recommendations. Please try again.",
            )

        return {
            "id": record.id,
            "recommendations": recommendations,
            "created_at": record.created_at,
        }


    