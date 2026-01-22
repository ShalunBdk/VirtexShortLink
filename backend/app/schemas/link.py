from pydantic import BaseModel, HttpUrl, Field
from typing import Optional
from datetime import datetime


class LinkCreate(BaseModel):
    """Schema for creating a new short link"""
    url: str = Field(..., description="Original URL to shorten", min_length=1, max_length=2048)
    custom_alias: Optional[str] = Field(None, description="Custom alias for short code", min_length=3, max_length=20)


class LinkUpdate(BaseModel):
    """Schema for updating a link"""
    original_url: Optional[str] = Field(None, min_length=1, max_length=2048)
    is_active: Optional[bool] = None


class LinkResponse(BaseModel):
    """Schema for link response"""
    id: int
    short_code: str
    original_url: str
    short_url: str
    created_at: datetime
    created_by: Optional[str] = None
    clicks_count: int
    unique_clicks_count: int = 0
    is_active: bool

    class Config:
        from_attributes = True


class LinkStats(BaseModel):
    """Schema for link statistics"""
    id: int
    short_code: str
    original_url: str
    clicks_count: int
    created_at: datetime
    recent_clicks: list

    class Config:
        from_attributes = True
