from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel


class TimeSeriesPoint(BaseModel):
    """Single point in time series data"""
    timestamp: str  # ISO date or hour string
    clicks: int
    unique_clicks: int


class CountryStats(BaseModel):
    """Country-level statistics"""
    country_code: Optional[str]
    country_name: Optional[str]
    clicks: int
    percentage: float


class CityStats(BaseModel):
    """City-level statistics"""
    city: Optional[str]
    country_code: Optional[str]
    clicks: int


class RefererStats(BaseModel):
    """Referer statistics"""
    referer: Optional[str]
    clicks: int
    percentage: float


class LinkAnalytics(BaseModel):
    """Complete analytics for a link"""
    link_id: int
    short_code: str
    period: str  # "24h", "7d", "30d", "90d"
    total_clicks: int
    unique_clicks: int
    qr_clicks: int = 0  # Clicks from QR code scans
    unique_ratio: float
    clicks_by_time: List[TimeSeriesPoint]
    clicks_by_country: List[CountryStats]
    clicks_by_city: List[CityStats]
    top_referers: List[RefererStats]
