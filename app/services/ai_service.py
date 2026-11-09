# app/services/ai_service.py

from google import genai
from app.core.config import GEMINI_API_KEY
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.content_generation import ContentGeneration

client = genai.Client(api_key=GEMINI_API_KEY)


class AIService:

    @staticmethod
    def generate_content(
        db: Session,
        user_id: int,
        platform: str,
        content_type: str,
        topic: str,
        target_audience: list[str],
        tone: str,
        language: str,
        notes: str | None = None
    ) -> str:
        
        # Audience ko readable format me convert karein
        audience_str = ", ".join(target_audience).replace("_", " ").title() if target_audience else "General Audience"
        
        # 🔥 Language Instruction (Strict)
        language_map = {
            "English": "in English language only.",
            "Urdu": "in Urdu language using proper Urdu (Nastaliq) script (اردو رسم الخط). DO NOT use Roman Urdu.",
            "Roman Urdu": "in Roman Urdu (Urdu written using English letters).",
            "Hindi": "in Hindi language using Devanagari script (हिंदी). DO NOT use Roman Hindi.",
            "Arabic": "in Arabic language using Arabic script (اللغة العربية).",
        }
        language_instruction = language_map.get(language, "in English language only.")

        # 🔥 Content Type ke hisaab se format instructions
        format_instructions = ""
        
        if content_type == "video":
            format_instructions = """
            Format: A well-structured YouTube/Video Script.
            - Include an engaging Hook (first 5 seconds).
            - Main Body (explain the topic).
            - Call to Action (CTA) at the end.
            """
        elif content_type == "adcopy":
            format_instructions = """
            Format: High-converting Ad Copy.
            - Include a Catchy Headline.
            - Primary Text (2-3 short paragraphs).
            - Clear Call to Action (CTA).
            - Suggested Hashtags (if platform is Instagram/Twitter).
            """
        elif content_type == "product":
            format_instructions = """
            Format: Detailed Product Description.
            - Catchy Product Title.
            - Key Features (bullet points).
            - Benefits (why it matters to the audience).
            - Closing line with purchase prompt.
            """
        else:
            # Fallback (agar future me koi naya type aaye)
            format_instructions = "Format: Provide a well-structured, engaging content piece."

        # 🔥 Master Prompt
        prompt = f"""
        You are an expert marketing copywriter and content strategist.
        
        **Task:** Generate content based on the following details.
        
        **Context:**
        - Platform: {platform}
        - Content Type: {content_type}
        - Topic/Product: {topic}
        - Target Audience: {audience_str}
        - Tone of Voice: {tone}
        
        **Format Instructions:**
        {format_instructions}
        
        **🔥 CRITICAL REQUIREMENT:**
        1. You MUST generate the entire content {language_instruction}
        2. You MUST tailor the vocabulary, slang, and references specifically for a **{audience_str}** audience.
        3. Maintain a **{tone}** tone throughout.
        4. ONLY return the final content. No introductory remarks like "Here is your content".
        
        **Extra Instructions from User:** 
        {notes if notes else "None"}
        """

        try:
            response = client.models.generate_content(
                model="gemini-3.1-flash-lite",
                contents=prompt,
            )
            
            if not response.text:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="AI generated an empty response. Please try again."
                )
                
            generated_text = response.text.strip()
            
            # DB me save karein
            content_record = ContentGeneration(
                user_id=user_id,
                platform=platform,
                content_type=content_type,
                topic=topic,
                target_audience=target_audience,
                tone=tone,
                language=language,
                notes=notes,
                generated_content=generated_text
            )
            db.add(content_record)
            db.commit()
            db.refresh(content_record)
            
            return generated_text

        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            print(f"Gemini API Error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate content. Please try again later."
            )

        