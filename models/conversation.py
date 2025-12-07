from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ConservationCreate(BaseModel):
    title: Optional[str] = None
    conversation_id: Optional[int] = Field(None, description="Use to continue existing conversation")


class ConservationResponse(BaseModel):
    id: int
    title: Optional[str]
    user_id: Optional[int]
    last_update: datetime

    class Config:
        from_attributes = True


class ConservationDetailResponse(BaseModel):
    id: int
    conversation_id: int
    role: str
    message: str
    created_at: datetime

    class Config:
        from_attributes = True
