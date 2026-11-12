# app/services/campaign_service.py

from google import genai
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.core.config import GEMINI_CAMPAIGN_API_KEY  # 🔥 Nayi Key Import
from app.models.campaign import Campaign
from app.models.business_profile import BusinessProfile
from datetime import datetime
import json
import re


# 🔥 Campaign ke liye alag client
client = genai.Client(api_key=GEMINI_CAMPAIGN_API_KEY)


class CampaignService:

    @staticmethod
    def generate_campaign_plan(
        db: Session,
        user_id: int,
        campaign_data: dict,
    ) -> dict:
        
        # 🔥 1. Business Profile DB se nikaalein
        business_id = campaign_data.get("business_id")
        business = None
        if business_id:
            business = db.query(BusinessProfile).filter(
                BusinessProfile.id == business_id,
                BusinessProfile.user_id == user_id
            ).first()

        # 2. Business details (Fallback ke sath)
        biz_name = business.business_name if business else "N/A"
        biz_type = business.business_type if business else "N/A"
        biz_goals = business.business_goals if business and business.business_goals else "N/A"
        biz_desc = business.business_description if business and business.business_description else "N/A"
        
        # 3. Audience & Services from Form (User changes allowed)
        audience_str = ", ".join(campaign_data.get("target_audience", [])) or "General Audience"
        
        # 🔥 4. Master Prompt
        prompt = f"""
        You are an expert marketing strategist and campaign planner.
        Generate a detailed marketing campaign plan in JSON format based on the following details.
        
        ### Campaign Details (From User Form):
        - Campaign Name: {campaign_data['campaign_name']}
        - Objective: {campaign_data['objective']}
        - Product / Service: {campaign_data['product_service']}
        - Target Audience: {audience_str}
        - Channels: {", ".join(campaign_data.get('channels', []))}
        - Budget: {campaign_data.get('budget', 0)} {campaign_data.get('currency', 'USD')}
        - Duration: {campaign_data.get('start_date')} to {campaign_data.get('end_date')}
        - Tone: {campaign_data['tone']}
        - Additional Instructions: {campaign_data.get('notes', 'None')}

        ### Business Context (From User's Business Profile):
        - Business Name: {biz_name}
        - Business Type: {biz_type}
        - Business Goals: {biz_goals}
        - Business Description: {biz_desc}

        ### Required Output Format (JSON Only, no markdown):
        {{
            "title": "Catchy Campaign Title",
            "objective": "Same as input objective but formatted nicely",
            "description": "A short 1-2 line campaign description",
            "strategy": "Detailed AI campaign strategy (2-3 paragraphs)",
            "channels": [
                {{"id": "instagram", "label": "Instagram"}},
                {{"id": "facebook", "label": "Facebook"}}
            ],
            "weeks": [
                {{
                    "title": "Week 1",
                    "items": ["Action item 1", "Action item 2", "Action item 3"]
                }},
                {{
                    "title": "Week 2",
                    "items": ["Action item 1", "Action item 2"]
                }}
            ],
            "ideas": ["Content idea 1", "Content idea 2", "Content idea 3"],
            "kpis": ["KPI 1", "KPI 2", "KPI 3"],
            "budget": [
                {{"label": "Social Media Ads", "pct": 40}},
                {{"label": "Content Creation", "pct": 30}},
                {{"label": "Influencer Marketing", "pct": 30}}
            ]
        }}

        IMPORTANT RULES:
        1. Respond with VALID JSON only. No markdown code blocks, no extra text.
        2. Make sure the 'channels' array only contains channels mentioned in the user input.
        3. Make sure the 'budget' percentages sum up to exactly 100.
        4. The strategy must be tailored to the business type and goals mentioned in the Business Context.
        """

        try:
            # 🔥 5. AI Call (Ab nayi API key use ho rahi hai)
            response = client.models.generate_content(
                model="gemini-3.1-flash-lite",
                contents=prompt,
            )
            
            if not response.text:
                raise HTTPException(status_code=500, detail="AI generated an empty response.")

            # 🔥 6. JSON Parse (Markdown code blocks remove karein)
            text = response.text.strip()
            text = re.sub(r'^```json\s*', '', text)
            text = re.sub(r'^```\s*', '', text)
            text = re.sub(r'\s*```$', '', text)
            
            plan_data = json.loads(text)

            # Total budget display ke liye
            total_budget_str = f"{campaign_data.get('currency', 'USD')} {campaign_data.get('budget', 0)}"
            plan_data["total"] = total_budget_str

            # 🔥 7. DB me save karein
            campaign_record = Campaign(
                user_id=user_id,
                business_id=business_id,
                campaign_name=campaign_data['campaign_name'],
                objective=campaign_data['objective'],
                product_service=campaign_data['product_service'],
                target_audience=campaign_data.get('target_audience', []),
                channels=campaign_data.get('channels', []),
                budget=campaign_data.get('budget', 0),
                currency=campaign_data.get('currency', 'USD'),
                start_date=campaign_data.get('start_date'),
                end_date=campaign_data.get('end_date'),
                tone=campaign_data['tone'],
                notes=campaign_data.get('notes', ''),
                generated_plan=plan_data
            )
            db.add(campaign_record)
            db.commit()
            db.refresh(campaign_record)

            return {
                "campaign_id": campaign_record.id,
                "campaign": plan_data
            }

        except json.JSONDecodeError as e:
            db.rollback()
            print(f"JSON Parse Error: {e}\nRaw Text: {response.text}")
            raise HTTPException(
                status_code=500, 
                detail="AI returned invalid JSON format. Please try again."
            )
        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            print(f"Campaign Error: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to generate campaign. Try again.")