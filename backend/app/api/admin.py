from typing import List, Optional, Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from ..database import get_db
from ..models import Link, Click, User, IPBlacklist, BitrixUser
from ..schemas.link import LinkResponse, LinkUpdate, LinkStats
from ..schemas.analytics import LinkAnalytics
from ..core.security import get_current_user
from ..services.analytics import get_link_analytics
from ..config import settings

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/links")
async def get_all_links(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = None,
    active_only: bool = False,
    owner_type: Optional[str] = Query(None, description="Filter by owner type: anonymous, bitrix, admin"),
    owner_id: Optional[int] = Query(None, description="Filter by specific Bitrix user ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all links with pagination and filtering.

    Requires authentication.
    """
    query = db.query(Link)

    # Filter by active status
    if active_only:
        query = query.filter(Link.is_active == True)

    # Filter by owner type
    if owner_type:
        query = query.filter(Link.owner_type == owner_type)

    # Filter by specific owner
    if owner_id:
        query = query.filter(Link.owner_id == owner_id)

    # Search by short_code or original_url
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (func.lower(Link.short_code).like(search_pattern.lower())) |
            (func.lower(Link.original_url).like(search_pattern.lower()))
        )

    # Order by most recent first
    query = query.order_by(desc(Link.created_at))

    # Pagination
    links = query.offset(skip).limit(limit).all()

    # Add short_url and owner info to each link
    result = []
    for link in links:
        # Get owner info if bitrix user
        owner_name = None
        owner_domain = None
        if link.owner_id and link.owner:
            owner_name = link.owner.name or f"User {link.owner.bitrix_user_id}"
            owner_domain = link.owner.bitrix_domain

        link_dict = {
            "id": link.id,
            "short_code": link.short_code,
            "original_url": link.original_url,
            "short_url": f"{settings.BASE_URL}/{link.short_code}",
            "created_at": link.created_at,
            "created_by": link.created_by,
            "clicks_count": link.clicks_count,
            "unique_clicks_count": link.unique_clicks_count,
            "is_active": link.is_active,
            "owner_type": link.owner_type or "anonymous",
            "owner_id": link.owner_id,
            "owner_name": owner_name,
            "owner_domain": owner_domain
        }
        result.append(link_dict)

    return result


@router.get("/bitrix-users")
async def get_bitrix_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get list of all Bitrix24 users who have created links.

    Requires authentication.
    """
    users = db.query(BitrixUser).order_by(BitrixUser.created_at.desc()).all()

    result = []
    for user in users:
        links_count = db.query(func.count(Link.id)).filter(Link.owner_id == user.id).scalar()
        result.append({
            "id": user.id,
            "bitrix_user_id": user.bitrix_user_id,
            "bitrix_domain": user.bitrix_domain,
            "name": user.name,
            "created_at": user.created_at,
            "links_count": links_count
        })

    return result


@router.get("/links/{link_id}", response_model=LinkResponse)
async def get_link_by_id(
    link_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific link by ID.

    Requires authentication.
    """
    link = db.query(Link).filter(Link.id == link_id).first()

    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    return {
        "id": link.id,
        "short_code": link.short_code,
        "original_url": link.original_url,
        "short_url": f"{settings.BASE_URL}/{link.short_code}",
        "created_at": link.created_at,
        "created_by": link.created_by,
        "clicks_count": link.clicks_count,
        "unique_clicks_count": link.unique_clicks_count,
        "is_active": link.is_active
    }


@router.put("/links/{link_id}", response_model=LinkResponse)
async def update_link(
    link_id: int,
    link_update: LinkUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a link.

    Requires authentication.
    """
    link = db.query(Link).filter(Link.id == link_id).first()

    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    # Update fields
    if link_update.original_url is not None:
        link.original_url = link_update.original_url

    if link_update.is_active is not None:
        link.is_active = link_update.is_active

    db.commit()
    db.refresh(link)

    return {
        "id": link.id,
        "short_code": link.short_code,
        "original_url": link.original_url,
        "short_url": f"{settings.BASE_URL}/{link.short_code}",
        "created_at": link.created_at,
        "created_by": link.created_by,
        "clicks_count": link.clicks_count,
        "unique_clicks_count": link.unique_clicks_count,
        "is_active": link.is_active
    }


@router.delete("/links/{link_id}")
async def delete_link(
    link_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a link.

    Requires authentication.
    """
    link = db.query(Link).filter(Link.id == link_id).first()

    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    db.delete(link)
    db.commit()

    return {"message": "Link deleted successfully"}


@router.patch("/links/{link_id}/toggle")
async def toggle_link_status(
    link_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Toggle link active status.

    Requires authentication.
    """
    link = db.query(Link).filter(Link.id == link_id).first()

    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    link.is_active = not link.is_active
    db.commit()

    return {
        "message": "Link status updated",
        "is_active": link.is_active
    }


@router.get("/stats/overview")
async def get_overview_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get overview statistics.

    Requires authentication.
    """
    total_links = db.query(func.count(Link.id)).scalar()
    active_links = db.query(func.count(Link.id)).filter(Link.is_active == True).scalar()
    total_clicks = db.query(func.sum(Link.clicks_count)).scalar() or 0
    total_unique_clicks = db.query(func.sum(Link.unique_clicks_count)).scalar() or 0

    # Top 10 links by clicks
    top_links = db.query(Link).order_by(desc(Link.clicks_count)).limit(10).all()

    top_links_data = [
        {
            "short_code": link.short_code,
            "original_url": link.original_url,
            "clicks_count": link.clicks_count,
            "unique_clicks_count": link.unique_clicks_count,
            "short_url": f"{settings.BASE_URL}/{link.short_code}"
        }
        for link in top_links
    ]

    return {
        "total_links": total_links,
        "active_links": active_links,
        "total_clicks": total_clicks,
        "total_unique_clicks": total_unique_clicks,
        "top_links": top_links_data
    }


@router.get("/links/{link_id}/stats")
async def get_link_stats(
    link_id: int,
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed statistics for a specific link.

    Requires authentication.
    """
    link = db.query(Link).filter(Link.id == link_id).first()

    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    # Get recent clicks
    recent_clicks = db.query(Click).filter(
        Click.link_id == link_id
    ).order_by(desc(Click.clicked_at)).limit(limit).all()

    clicks_data = [
        {
            "clicked_at": click.clicked_at,
            "ip_address": click.ip_address,
            "user_agent": click.user_agent[:100] if click.user_agent else None,
            "referer": click.referer
        }
        for click in recent_clicks
    ]

    return {
        "id": link.id,
        "short_code": link.short_code,
        "original_url": link.original_url,
        "clicks_count": link.clicks_count,
        "created_at": link.created_at,
        "recent_clicks": clicks_data
    }


@router.post("/blacklist/{ip_address}")
async def add_to_blacklist(
    ip_address: str,
    reason: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Add an IP address to blacklist.

    Requires authentication.
    """
    # Check if already blacklisted
    existing = db.query(IPBlacklist).filter(
        IPBlacklist.ip_address == ip_address
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="IP already blacklisted")

    # Add to blacklist
    blacklist_entry = IPBlacklist(
        ip_address=ip_address,
        reason=reason or "Spam/abuse"
    )

    db.add(blacklist_entry)
    db.commit()

    return {"message": f"IP {ip_address} added to blacklist"}


@router.delete("/blacklist/{ip_address}")
async def remove_from_blacklist(
    ip_address: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Remove an IP address from blacklist.

    Requires authentication.
    """
    entry = db.query(IPBlacklist).filter(
        IPBlacklist.ip_address == ip_address
    ).first()

    if not entry:
        raise HTTPException(status_code=404, detail="IP not in blacklist")

    db.delete(entry)
    db.commit()

    return {"message": f"IP {ip_address} removed from blacklist"}


@router.get("/links/{link_id}/clicks")
async def get_link_clicks(
    link_id: int,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed click history for a link.

    Requires authentication.
    """
    link = db.query(Link).filter(Link.id == link_id).first()

    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    # Get clicks with all details
    clicks = db.query(Click).filter(
        Click.link_id == link_id
    ).order_by(desc(Click.clicked_at)).offset(offset).limit(limit).all()

    total = db.query(func.count(Click.id)).filter(Click.link_id == link_id).scalar()

    clicks_data = [
        {
            "id": click.id,
            "clicked_at": click.clicked_at.isoformat() if click.clicked_at else None,
            "ip_address": click.ip_address,
            "user_agent": click.user_agent,
            "referer": click.referer,
            "country_code": click.country_code,
            "country_name": click.country_name,
            "city": click.city,
            "is_unique": click.is_unique
        }
        for click in clicks
    ]

    return {
        "link_id": link_id,
        "total": total,
        "limit": limit,
        "offset": offset,
        "clicks": clicks_data
    }


@router.get("/links/{link_id}/analytics", response_model=LinkAnalytics)
async def get_link_analytics_endpoint(
    link_id: int,
    period: Literal["24h", "7d", "30d", "90d"] = Query("7d"),
    group_by: Literal["hour", "day"] = Query("day"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed analytics for a specific link.

    Query params:
    - period: "24h" | "7d" | "30d" | "90d" (default: "7d")
    - group_by: "hour" | "day" (default: "day")

    Requires authentication.
    """
    link = db.query(Link).filter(Link.id == link_id).first()

    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    return get_link_analytics(db, link, period, group_by)
