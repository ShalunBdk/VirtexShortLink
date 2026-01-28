from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import RedirectResponse, HTMLResponse, StreamingResponse
from sqlalchemy.orm import Session
from pathlib import Path
from sqlalchemy import func
from slowapi import Limiter
from slowapi.util import get_remote_address
import io

from ..database import get_db
from ..models import Link, Click
from ..schemas.link import LinkCreate, LinkResponse
from ..core.shortener import generate_short_code, validate_custom_alias, is_code_available
from ..utils.validators import is_valid_url, is_spam_url, is_ip_blacklisted, get_client_ip, parse_user_agent_os
from ..utils.geo import get_geo_data, check_unique_visitor, record_unique_visitor
from ..config import settings

# Try to import qrcode, handle if not installed
try:
    import qrcode
    from qrcode.image.styledpil import StyledPilImage
    from qrcode.image.styles.moduledrawers import RoundedModuleDrawer
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


def get_404_page() -> str:
    """Load 404 error page"""
    try:
        # Use absolute path for Docker compatibility
        frontend_path = Path("/app/frontend")
        if not frontend_path.exists():
            # Fallback for local development
            frontend_path = Path(__file__).parent.parent.parent.parent / "frontend"

        error_page = frontend_path / "404.html"
        if error_page.exists():
            return error_page.read_text(encoding='utf-8')
    except Exception:
        pass

    # Fallback HTML if file not found
    return """
    <!DOCTYPE html>
    <html><head><meta charset="UTF-8"><title>Ссылка не найдена</title></head>
    <body style="font-family: Arial; text-align: center; padding: 50px;">
        <h1>404 - Ссылка не найдена</h1>
        <p>Запрошенная короткая ссылка не существует или была деактивирована.</p>
        <a href="/" style="color: #D64005;">Перейти на главную</a>
    </body></html>
    """


@router.post("/shorten", response_model=dict)
@limiter.limit(f"{settings.RATE_LIMIT_PER_HOUR}/hour")
async def create_short_link(
    request: Request,
    link_data: LinkCreate,
    db: Session = Depends(get_db)
):
    """
    Create a short link.

    Rate limited to prevent spam.
    """
    # Get client IP
    client_ip = get_client_ip(request)

    # Check if IP is blacklisted
    if is_ip_blacklisted(client_ip, db):
        raise HTTPException(
            status_code=403,
            detail="Access denied. Your IP has been blocked."
        )

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

    # Check if this URL already exists for anonymous users (deduplication within anonymous links only)
    # Bitrix24 users have their own deduplication in the /bitrix/api/links endpoint
    existing_link = db.query(Link).filter(
        Link.original_url == link_data.url,
        Link.is_active == True,
        Link.owner_id == None,  # Only check anonymous links
        Link.owner_type == 'anonymous'
    ).first()

    if existing_link:
        # Return existing link instead of creating a new one
        return {
            "short_url": f"{settings.BASE_URL}/{existing_link.short_code}",
            "short_code": existing_link.short_code,
            "original_url": existing_link.original_url,
            "existing": True
        }

    # Handle custom alias or generate code
    if link_data.custom_alias:
        # Validate custom alias
        is_valid_alias, error_msg = validate_custom_alias(link_data.custom_alias)
        if not is_valid_alias:
            raise HTTPException(status_code=400, detail=error_msg)

        # Check if alias is available (case-insensitive)
        if not is_code_available(link_data.custom_alias, db):
            raise HTTPException(
                status_code=400,
                detail=f"Alias '{link_data.custom_alias}' is already taken"
            )

        short_code = link_data.custom_alias.lower()
    else:
        # Generate random short code
        try:
            short_code = generate_short_code(
                length=settings.SHORT_CODE_LENGTH,
                db=db
            )
        except ValueError as e:
            raise HTTPException(status_code=500, detail=str(e))

    # Create link in database
    new_link = Link(
        short_code=short_code,
        original_url=link_data.url,
        created_by=client_ip
    )

    db.add(new_link)
    db.commit()
    db.refresh(new_link)

    # Return response
    return {
        "short_url": f"{settings.BASE_URL}/{short_code}",
        "short_code": short_code,
        "original_url": link_data.url,
        "existing": False
    }


@router.get("/qr/{short_code}")
async def get_qr_code(
    short_code: str,
    size: int = 10,
    db: Session = Depends(get_db)
):
    """
    Generate QR code for a short link.
    The QR code points to /q/{short_code} to track QR scans.

    Parameters:
    - size: QR code size (box_size), default 10
    """
    if not QR_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="QR code generation is not available. Install qrcode library."
        )

    # Find link
    link = db.query(Link).filter(
        func.lower(Link.short_code) == short_code.lower()
    ).first()

    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    if not link.is_active:
        raise HTTPException(status_code=410, detail="Link is inactive")

    # Generate QR code URL (uses /q/ prefix to track QR clicks)
    qr_url = f"{settings.BASE_URL}/q/{link.short_code}"

    # Create QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=size,
        border=2,
    )
    qr.add_data(qr_url)
    qr.make(fit=True)

    # Create image
    img = qr.make_image(fill_color="#D64005", back_color="white")

    # Save to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)

    return StreamingResponse(
        img_bytes,
        media_type="image/png",
        headers={
            "Content-Disposition": f"inline; filename=qr_{short_code}.png"
        }
    )


@router.get("/{short_code}")
async def redirect_to_url(
    short_code: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Redirect to the original URL from short code.

    Case-insensitive lookup.
    Records click statistics.
    """
    # Find link by short code (case-insensitive)
    link = db.query(Link).filter(
        func.lower(Link.short_code) == short_code.lower()
    ).first()

    if not link:
        # Return custom 404 page instead of exception
        response = HTMLResponse(content=get_404_page(), status_code=404)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    if not link.is_active:
        # Return custom 404 page for inactive links
        response = HTMLResponse(content=get_404_page(), status_code=410)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    # Get client info
    client_ip = get_client_ip(request)
    user_agent = request.headers.get('user-agent', '')[:512]
    referer = request.headers.get('referer', '')[:512]

    # Get geo data
    geo = get_geo_data(client_ip)

    # Check if unique visitor
    is_unique, user_agent_hash = check_unique_visitor(db, link.id, client_ip, user_agent)

    # Detect OS from user agent
    device_os = parse_user_agent_os(user_agent)

    # Record click statistics
    click = Click(
        link_id=link.id,
        ip_address=client_ip,
        user_agent=user_agent,
        referer=referer,
        country_code=geo.country_code,
        country_name=geo.country_name,
        city=geo.city,
        is_unique=is_unique,
        device_os=device_os
    )
    db.add(click)
    db.flush()  # Get click.id

    # Record unique visitor if new
    if is_unique:
        record_unique_visitor(db, link.id, client_ip, user_agent_hash, click.id)
        link.unique_clicks_count += 1

    # Increment click counter
    link.clicks_count += 1

    db.commit()

    # Redirect to original URL (302 for tracking)
    # Add headers to prevent caching
    response = RedirectResponse(url=link.original_url, status_code=302)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    return response
