"""
Pydantic-схемы запросов/ответов API.
Источник: hrm/api/schemas.py, упрощено для MVP.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    session_id: Optional[str] = None


class Citation(BaseModel):
    source_id: str
    source: str = ""
    breadcrumb: str = ""
    article_number: Optional[str] = None
    article_name: Optional[str] = None
    point_number: Optional[str] = None
    chunk_type: Optional[str] = None
    score: Optional[float] = None


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    citations: list[Citation] = []


class MessageOut(BaseModel):
    id: int
    from_ai: bool
    content: str
    created_at: datetime
    citations: list[Citation] = []


class SessionOut(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
