# app/api/routers/ai.py

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional
from sqlalchemy.orm import Session

from app.core.database import get_db  # 🔥 Import
from app.core.security import verify_access_token
from app.services.ai_service import AIService

router = APIRouter(
    prefix="/api/ai",
    tags=["AI Content Generation"]
)


class GenerateContentRequest(BaseModel):
    platform: str
    content_type: str
    topic: str = Field(..., min_length=2, max_length=200)
    target_audience: List[str] = []
    tone: str
    language: str
    notes: Optional[str] = None


@router.post("/generate", status_code=status.HTTP_200_OK)
def generate_ai_content(
    data: GenerateContentRequest,
    user_id: int = Depends(verify_access_token),
    db: Session = Depends(get_db)  # 🔥 DB session
):
    content = AIService.generate_content(
        db=db,                     # 🔥 Pass
        user_id=user_id,           # 🔥 Pass
        platform=data.platform,
        content_type=data.content_type,
        topic=data.topic,
        target_audience=data.target_audience,
        tone=data.tone,
        language=data.language,
        notes=data.notes
    )
    
    return {"content": content}