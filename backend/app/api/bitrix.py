from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta

from ..database import get_db
from ..models import Link, Click, BitrixUser
from ..schemas.bitrix import (
    BitrixLinkCreate,
    BitrixLinkResponse,
    BitrixLinkListResponse,
    BitrixLinkAnalytics,
    BitrixDeleteResponse,
)
from ..core.shortener import generate_short_code, validate_custom_alias, is_code_available
from ..utils.validators import is_valid_url, is_spam_url
from ..config import settings

router = APIRouter()


def get_frontend_path() -> Path:
    """Get frontend path for serving HTML files"""
    frontend_path = Path("/app/frontend")
    if not frontend_path.exists():
        frontend_path = Path(__file__).parent.parent.parent.parent / "frontend"
    return frontend_path


def get_or_create_bitrix_user(
    db: Session,
    user_id: str,
    domain: str,
    name: Optional[str] = None
) -> BitrixUser:
    """Get existing or create new Bitrix24 user"""
    user = db.query(BitrixUser).filter(
        BitrixUser.bitrix_user_id == user_id,
        BitrixUser.bitrix_domain == domain
    ).first()

    if not user:
        user = BitrixUser(
            bitrix_user_id=user_id,
            bitrix_domain=domain,
            name=name
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    elif name and user.name != name:
        user.name = name
        db.commit()

    return user


@router.get("/install", response_class=HTMLResponse)
async def bitrix_install(request: Request):
    """
    Bitrix24 application installation page.
    Called when the app is installed in a Bitrix24 portal.
    """
    frontend_path = get_frontend_path()
    install_file = frontend_path / "bitrix" / "install.html"

    if install_file.exists():
        return HTMLResponse(content=install_file.read_text(encoding='utf-8'))

    # Fallback installation page
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Установка приложения</title>
        <script src="//api.bitrix24.com/api/v1/"></script>
    </head>
    <body>
        <h1>Установка приложения Сокращатель ссылок</h1>
        <p>Приложение успешно установлено!</p>
        <script>
            BX24.init(function() {
                BX24.installFinish();
            });
        </script>
    </body>
    </html>
    """)


@router.post("/install", response_class=HTMLResponse)
async def bitrix_install_post(request: Request):
    """Handle POST request for installation (some Bitrix24 versions use POST)"""
    return await bitrix_install(request)


@router.get("/", response_class=HTMLResponse)
async def bitrix_cabinet(request: Request):
    """
    Bitrix24 personal cabinet page.
    Serves the main application interface inside Bitrix24 iframe.
    """
    frontend_path = get_frontend_path()
    index_file = frontend_path / "bitrix" / "index.html"

    if index_file.exists():
        return HTMLResponse(content=index_file.read_text(encoding='utf-8'))

    # Fallback cabinet page
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Сокращатель ссылок</title>
        <script src="//api.bitrix24.com/api/v1/"></script>
    </head>
    <body>
        <h1>Сокращатель ссылок</h1>
        <p>Интерфейс не загружен. Обратитесь к администратору.</p>
    </body>
    </html>
    """)


@router.post("/", response_class=HTMLResponse)
async def bitrix_cabinet_post(request: Request):
    """Handle POST request for cabinet (some Bitrix24 versions use POST)"""
    return await bitrix_cabinet(request)


@router.get("/analytics", response_class=HTMLResponse)
@router.get("/analytics.html", response_class=HTMLResponse)
async def bitrix_analytics_page(request: Request):
    """
    Bitrix24 analytics page for a specific link.
    """
    frontend_path = get_frontend_path()
    analytics_file = frontend_path / "bitrix" / "analytics.html"

    if analytics_file.exists():
        return HTMLResponse(content=analytics_file.read_text(encoding='utf-8'))

    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Аналитика</title>
    </head>
    <body>
        <h1>Аналитика</h1>
        <p>Страница не найдена.</p>
    </body>
    </html>
    """)


@router.get("/api/links", response_model=BitrixLinkListResponse)
async def get_user_links(
    user_id: str,
    domain: str,
    page: int = 1,
    per_page: int = 20,
    db: Session = Depends(get_db)
):
    """
    Get all links for a specific Bitrix24 user.
    """
    # Find or create user
    bitrix_user = get_or_create_bitrix_user(db, user_id, domain)

    # Query links
    query = db.query(Link).filter(
        Link.owner_id == bitrix_user.id,
        Link.owner_type == 'bitrix'
    ).order_by(Link.created_at.desc())

    total = query.count()
    links = query.offset((page - 1) * per_page).limit(per_page).all()

    items = [
        BitrixLinkResponse(
            id=link.id,
            short_code=link.short_code,
            original_url=link.original_url,
            short_url=f"{settings.BASE_URL}/{link.short_code}",
            created_at=link.created_at,
            clicks_count=link.clicks_count,
            unique_clicks_count=link.unique_clicks_count,
            is_active=link.is_active
        )
        for link in links
    ]

    return BitrixLinkListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page
    )


@router.post("/api/links", response_model=dict)
async def create_user_link(
    link_data: BitrixLinkCreate,
    db: Session = Depends(get_db)
):
    """
    Create a short link for a Bitrix24 user.
    Deduplication is done only within the user's own links.
    """
    # Validate URL
    is_valid, error_msg = is_valid_url(link_data.url)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    # Check for spam
    if is_spam_url(link_data.url):
        raise HTTPException(
            status_code=400,
            detail="URL appears to be spam and cannot be shortened"
        )

    # Get or create user
    bitrix_user = get_or_create_bitrix_user(db, link_data.user_id, link_data.domain, link_data.user_name)

    # Check if this URL already exists for this user (deduplication within user's links only)
    existing_link = db.query(Link).filter(
        Link.original_url == link_data.url,
        Link.owner_id == bitrix_user.id,
        Link.owner_type == 'bitrix',
        Link.is_active == True
    ).first()

    if existing_link:
        return {
            "short_url": f"{settings.BASE_URL}/{existing_link.short_code}",
            "short_code": existing_link.short_code,
            "original_url": existing_link.original_url,
            "id": existing_link.id,
            "existing": True
        }

    # Handle custom alias or generate code
    if link_data.custom_alias:
        is_valid_alias, error_msg = validate_custom_alias(link_data.custom_alias)
        if not is_valid_alias:
            raise HTTPException(status_code=400, detail=error_msg)

        if not is_code_available(link_data.custom_alias, db):
            raise HTTPException(
                status_code=400,
                detail=f"Alias '{link_data.custom_alias}' is already taken"
            )

        short_code = link_data.custom_alias.lower()
    else:
        try:
            short_code = generate_short_code(
                length=settings.SHORT_CODE_LENGTH,
                db=db
            )
        except ValueError as e:
            raise HTTPException(status_code=500, detail=str(e))

    # Create link
    new_link = Link(
        short_code=short_code,
        original_url=link_data.url,
        created_by=f"bitrix:{link_data.user_id}@{link_data.domain}",
        owner_id=bitrix_user.id,
        owner_type='bitrix'
    )

    db.add(new_link)
    db.commit()
    db.refresh(new_link)

    return {
        "short_url": f"{settings.BASE_URL}/{short_code}",
        "short_code": short_code,
        "original_url": link_data.url,
        "id": new_link.id,
        "existing": False
    }


@router.delete("/api/links/{link_id}", response_model=BitrixDeleteResponse)
async def delete_user_link(
    link_id: int,
    user_id: str,
    domain: str,
    db: Session = Depends(get_db)
):
    """
    Delete a link owned by a Bitrix24 user.
    Users can only delete their own links.
    """
    # Find user
    bitrix_user = db.query(BitrixUser).filter(
        BitrixUser.bitrix_user_id == user_id,
        BitrixUser.bitrix_domain == domain
    ).first()

    if not bitrix_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Find link
    link = db.query(Link).filter(
        Link.id == link_id,
        Link.owner_id == bitrix_user.id,
        Link.owner_type == 'bitrix'
    ).first()

    if not link:
        raise HTTPException(status_code=404, detail="Link not found or you don't have permission to delete it")

    # Delete link (cascades to clicks)
    db.delete(link)
    db.commit()

    return BitrixDeleteResponse(
        success=True,
        message="Link deleted successfully"
    )


@router.get("/api/links/{link_id}/analytics", response_model=BitrixLinkAnalytics)
async def get_link_analytics(
    link_id: int,
    user_id: str,
    domain: str,
    db: Session = Depends(get_db)
):
    """
    Get analytics for a specific link owned by a Bitrix24 user.
    """
    # Find user
    bitrix_user = db.query(BitrixUser).filter(
        BitrixUser.bitrix_user_id == user_id,
        BitrixUser.bitrix_domain == domain
    ).first()

    if not bitrix_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Find link
    link = db.query(Link).filter(
        Link.id == link_id,
        Link.owner_id == bitrix_user.id,
        Link.owner_type == 'bitrix'
    ).first()

    if not link:
        raise HTTPException(status_code=404, detail="Link not found or you don't have permission to view it")

    # Get clicks by day (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    clicks_by_day_raw = db.query(
        func.date(Click.clicked_at).label('date'),
        func.count(Click.id).label('count')
    ).filter(
        Click.link_id == link.id,
        Click.clicked_at >= thirty_days_ago
    ).group_by(func.date(Click.clicked_at)).all()

    clicks_by_day = [{"date": str(row.date), "count": row.count} for row in clicks_by_day_raw]

    # Get clicks by country
    clicks_by_country_raw = db.query(
        Click.country_name,
        func.count(Click.id).label('count')
    ).filter(
        Click.link_id == link.id,
        Click.country_name.isnot(None)
    ).group_by(Click.country_name).order_by(func.count(Click.id).desc()).limit(10).all()

    clicks_by_country = [{"country": row.country_name or "Unknown", "count": row.count} for row in clicks_by_country_raw]

    # Get recent clicks
    recent_clicks_raw = db.query(Click).filter(
        Click.link_id == link.id
    ).order_by(Click.clicked_at.desc()).limit(20).all()

    recent_clicks = [
        {
            "id": click.id,
            "created_at": click.clicked_at.isoformat() if click.clicked_at else None,
            "ip_address": click.ip_address[:10] + "..." if click.ip_address and len(click.ip_address) > 10 else click.ip_address,
            "country": click.country_name,
            "city": click.city,
            "is_unique": click.is_unique,
            "is_qr": getattr(click, 'is_qr_click', False)
        }
        for click in recent_clicks_raw
    ]

    # Count QR clicks
    qr_clicks_count = db.query(func.count(Click.id)).filter(
        Click.link_id == link.id,
        Click.is_qr_click == True
    ).scalar() or 0

    return BitrixLinkAnalytics(
        link_id=link.id,
        short_code=link.short_code,
        original_url=link.original_url,
        clicks_count=link.clicks_count,
        unique_clicks_count=link.unique_clicks_count,
        qr_clicks_count=qr_clicks_count,
        created_at=link.created_at,
        clicks_by_day=clicks_by_day,
        clicks_by_country=clicks_by_country,
        recent_clicks=recent_clicks
    )
