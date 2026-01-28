from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class BitrixUserInfo(BaseModel):
    """Schema for Bitrix24 user information"""
    user_id: str = Field(..., description="User ID from Bitrix24")
    domain: str = Field(..., description="Bitrix24 portal domain")
    name: Optional[str] = Field(None, description="User display name")


class BitrixLinkCreate(BaseModel):
    """Schema for creating a link via Bitrix24"""
    url: str = Field(..., description="Original URL to shorten", min_length=1, max_length=2048)
    custom_alias: Optional[str] = Field(None, description="Custom alias for short code", min_length=3, max_length=20)
    user_id: str = Field(..., description="Bitrix24 user ID")
    domain: str = Field(..., description="Bitrix24 portal domain")
    user_name: Optional[str] = Field(None, description="User display name (e.g. 'Шишкин А.А.')")


class BitrixLinkResponse(BaseModel):
    """Schema for link response in Bitrix24 cabinet"""
    id: int
    short_code: str
    original_url: str
    short_url: str
    created_at: datetime
    clicks_count: int
    unique_clicks_count: int
    is_active: bool

    class Config:
        from_attributes = True


class BitrixLinkListResponse(BaseModel):
    """Schema for paginated link list"""
    items: List[BitrixLinkResponse]
    total: int
    page: int
    per_page: int


class BitrixLinkAnalytics(BaseModel):
    """Schema for link analytics in Bitrix24 cabinet"""
    link_id: int
    short_code: str
    original_url: str
    clicks_count: int
    unique_clicks_count: int
    qr_clicks_count: int = 0
    created_at: datetime
    clicks_by_day: List[dict]
    clicks_by_country: List[dict]
    recent_clicks: List[dict]


class BitrixDeleteResponse(BaseModel):
    """Schema for delete operation response"""
    success: bool
    message: str
