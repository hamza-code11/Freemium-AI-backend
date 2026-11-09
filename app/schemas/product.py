from pydantic import BaseModel, Field, ConfigDict
from typing import Optional


# Request Schema
class ProductCreate(BaseModel):

    name: str = Field(
        min_length=3,
        max_length=255
    )

    description: Optional[str] = None


# Response Schema
class ProductResponse(BaseModel):

    id: int
    name: str
    description: Optional[str] = None
    image: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
    