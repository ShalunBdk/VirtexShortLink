from datetime import datetime, timedelta
from typing import List
from sqlalchemy import func, Integer
from sqlalchemy.orm import Session

from ..models import Click, Link


def get_period_start(period: str) -> datetime:
    """Get start datetime for given period"""
    now = datetime.utcnow()
    if period == "24h":
        return now - timedelta(hours=24)
    elif period == "7d":
        return now - timedelta(days=7)
    elif period == "30d":
        return now - timedelta(days=30)
    elif period == "90d":
        return now - timedelta(days=90)
    return now - timedelta(days=7)  # default


def get_clicks_by_day(db: Session, link_id: int, period: str) -> List[dict]:
    """Get clicks aggregated by day"""
    start_date = get_period_start(period)

    # SQLite compatible date extraction
    results = db.query(
        func.date(Click.clicked_at).label('date'),
        func.count(Click.id).label('clicks'),
        func.sum(func.cast(Click.is_unique, Integer)).label('unique_clicks')
    ).filter(
        Click.link_id == link_id,
        Click.clicked_at >= start_date
    ).group_by(
        func.date(Click.clicked_at)
    ).order_by(
        func.date(Click.clicked_at)
    ).all()

    return [
        {
            "timestamp": row.date if isinstance(row.date, str) else row.date.isoformat() if row.date else "",
            "clicks": row.clicks,
            "unique_clicks": row.unique_clicks or 0
        }
        for row in results
    ]


def get_clicks_by_hour(db: Session, link_id: int) -> List[dict]:
    """Get clicks for last 24 hours aggregated by hour"""
    start_time = datetime.utcnow() - timedelta(hours=24)

    # SQLite compatible hour extraction
    results = db.query(
        func.strftime('%Y-%m-%d %H:00', Click.clicked_at).label('hour'),
        func.count(Click.id).label('clicks'),
        func.sum(func.cast(Click.is_unique, Integer)).label('unique_clicks')
    ).filter(
        Click.link_id == link_id,
        Click.clicked_at >= start_time
    ).group_by(
        func.strftime('%Y-%m-%d %H:00', Click.clicked_at)
    ).order_by(
        func.strftime('%Y-%m-%d %H:00', Click.clicked_at)
    ).all()

    return [
        {
            "timestamp": row.hour or "",
            "clicks": row.clicks,
            "unique_clicks": row.unique_clicks or 0
        }
        for row in results
    ]


def get_clicks_by_country(db: Session, link_id: int, period: str) -> List[dict]:
    """Get clicks aggregated by country"""
    start_date = get_period_start(period)

    results = db.query(
        Click.country_code,
        Click.country_name,
        func.count(Click.id).label('clicks')
    ).filter(
        Click.link_id == link_id,
        Click.clicked_at >= start_date
    ).group_by(
        Click.country_code,
        Click.country_name
    ).order_by(
        func.count(Click.id).desc()
    ).limit(20).all()

    total = sum(row.clicks for row in results)

    return [
        {
            "country_code": row.country_code,
            "country_name": row.country_name or "Unknown",
            "clicks": row.clicks,
            "percentage": round(row.clicks / total * 100, 1) if total > 0 else 0
        }
        for row in results
    ]


def get_clicks_by_city(db: Session, link_id: int, period: str, limit: int = 10) -> List[dict]:
    """Get top cities by clicks"""
    start_date = get_period_start(period)

    results = db.query(
        Click.city,
        Click.country_code,
        func.count(Click.id).label('clicks')
    ).filter(
        Click.link_id == link_id,
        Click.clicked_at >= start_date,
        Click.city.isnot(None)
    ).group_by(
        Click.city,
        Click.country_code
    ).order_by(
        func.count(Click.id).desc()
    ).limit(limit).all()

    return [
        {
            "city": row.city,
            "country_code": row.country_code,
            "clicks": row.clicks
        }
        for row in results
    ]


def get_clicks_by_os(db: Session, link_id: int, period: str, limit: int = 10) -> List[dict]:
    """Get clicks aggregated by operating system"""
    start_date = get_period_start(period)

    results = db.query(
        Click.device_os,
        func.count(Click.id).label('clicks')
    ).filter(
        Click.link_id == link_id,
        Click.clicked_at >= start_date
    ).group_by(
        Click.device_os
    ).order_by(
        func.count(Click.id).desc()
    ).limit(limit).all()

    total = sum(row.clicks for row in results)

    return [
        {
            "os": row.device_os or "Unknown",
            "clicks": row.clicks,
            "percentage": round(row.clicks / total * 100, 1) if total > 0 else 0
        }
        for row in results
    ]


def get_top_referers(db: Session, link_id: int, period: str, limit: int = 10) -> List[dict]:
    """Get top referer sources"""
    start_date = get_period_start(period)

    results = db.query(
        Click.referer,
        func.count(Click.id).label('clicks')
    ).filter(
        Click.link_id == link_id,
        Click.clicked_at >= start_date
    ).group_by(
        Click.referer
    ).order_by(
        func.count(Click.id).desc()
    ).limit(limit).all()

    total = sum(row.clicks for row in results)

    return [
        {
            "referer": row.referer if row.referer else "Direct",
            "clicks": row.clicks,
            "percentage": round(row.clicks / total * 100, 1) if total > 0 else 0
        }
        for row in results
    ]


def get_link_analytics(db: Session, link: Link, period: str, group_by: str = "day") -> dict:
    """Get complete analytics for a link"""
    # Get time series data
    if group_by == "hour":
        clicks_by_time = get_clicks_by_hour(db, link.id)
    else:
        clicks_by_time = get_clicks_by_day(db, link.id, period)

    # Get aggregated data
    clicks_by_country = get_clicks_by_country(db, link.id, period)
    clicks_by_city = get_clicks_by_city(db, link.id, period)
    clicks_by_os = get_clicks_by_os(db, link.id, period)
    top_referers = get_top_referers(db, link.id, period)

    # Calculate totals for period
    start_date = get_period_start(period)
    total_clicks = db.query(func.count(Click.id)).filter(
        Click.link_id == link.id,
        Click.clicked_at >= start_date
    ).scalar() or 0

    unique_clicks = db.query(func.count(Click.id)).filter(
        Click.link_id == link.id,
        Click.clicked_at >= start_date,
        Click.is_unique == True
    ).scalar() or 0

    # QR clicks count
    qr_clicks = db.query(func.count(Click.id)).filter(
        Click.link_id == link.id,
        Click.clicked_at >= start_date,
        Click.is_qr_click == True
    ).scalar() or 0

    unique_ratio = round(unique_clicks / total_clicks, 2) if total_clicks > 0 else 0

    return {
        "link_id": link.id,
        "short_code": link.short_code,
        "period": period,
        "total_clicks": total_clicks,
        "unique_clicks": unique_clicks,
        "qr_clicks": qr_clicks,
        "unique_ratio": unique_ratio,
        "clicks_by_time": clicks_by_time,
        "clicks_by_country": clicks_by_country,
        "clicks_by_city": clicks_by_city,
        "clicks_by_os": clicks_by_os,
        "top_referers": top_referers
    }
