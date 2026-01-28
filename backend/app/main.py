from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from pathlib import Path

from .database import engine, Base
from .api import links, auth, admin
from .api import bitrix as bitrix_api
from .config import settings

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title="Virtex Food Short Links",
    description="Corporate URL shortening service for Virtex Food",
    version="1.0.0"
)

# Setup rate limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Session middleware for Bitrix24 integration
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SESSION_SECRET_KEY,
    same_site="none",
    https_only=True
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files - use absolute path for Docker compatibility
# In Docker: /app/frontend, Locally: ../../../frontend from this file
frontend_path = Path("/app/frontend")
if not frontend_path.exists():
    # Fallback for local development
    frontend_path = Path(__file__).parent.parent.parent / "frontend"

if frontend_path.exists() and (frontend_path / "static").exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path / "static")), name="static")

# Include routers
app.include_router(auth.router, prefix="/api", tags=["auth"])
app.include_router(admin.router, prefix="/api", tags=["admin"])
app.include_router(links.router, prefix="/api", tags=["links"])
app.include_router(bitrix_api.router, prefix="/bitrix", tags=["bitrix"])

# Root endpoint - serve main page
@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main shortening page"""
    index_file = frontend_path / "index.html"
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text(encoding='utf-8'))
    return HTMLResponse(content="<h1>Virtex Food Short Links</h1><p>Service is running.</p>")


# Bitrix24 POST handler at root (Bitrix sends POST requests with DOMAIN parameter)
@app.post("/", response_class=HTMLResponse)
async def root_post(request: Request):
    """Handle Bitrix24 POST requests at root"""
    # Check if this is a Bitrix24 request (has DOMAIN parameter)
    domain = request.query_params.get("DOMAIN")
    if domain:
        # Serve Bitrix24 cabinet
        bitrix_file = frontend_path / "bitrix" / "index.html"
        if bitrix_file.exists():
            return HTMLResponse(content=bitrix_file.read_text(encoding='utf-8'))
        return HTMLResponse(content="<h1>Bitrix24 Cabinet</h1><p>Interface not loaded.</p>")

    # Regular POST to root - return main page
    index_file = frontend_path / "index.html"
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text(encoding='utf-8'))
    return HTMLResponse(content="<h1>Virtex Food Short Links</h1><p>Service is running.</p>")


# Admin panel endpoint
@app.get("/admin", response_class=HTMLResponse)
@app.get("/admin/", response_class=HTMLResponse)
async def admin_panel():
    """Serve the admin panel"""
    admin_file = frontend_path / "admin" / "index.html"
    if admin_file.exists():
        return HTMLResponse(content=admin_file.read_text(encoding='utf-8'))
    return HTMLResponse(content="<h1>Admin Panel</h1><p>Coming soon...</p>")


# Admin analytics page
@app.get("/admin/analytics.html", response_class=HTMLResponse)
@app.get("/admin/analytics", response_class=HTMLResponse)
async def admin_analytics():
    """Serve the admin analytics page"""
    analytics_file = frontend_path / "admin" / "analytics.html"
    if analytics_file.exists():
        return HTMLResponse(content=analytics_file.read_text(encoding='utf-8'))
    return HTMLResponse(content="<h1>Analytics</h1><p>Page not found.</p>", status_code=404)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Virtex Food Short Links"}


# QR code redirect endpoint (tracks QR scans)
from .api.links import redirect_to_url
from fastapi import Depends
from sqlalchemy.orm import Session
from .database import get_db
from .models import Link, Click
from .utils.validators import get_client_ip
from .utils.geo import get_geo_data, check_unique_visitor, record_unique_visitor
from fastapi.responses import RedirectResponse
from sqlalchemy import func as sql_func


@app.get("/q/{short_code}")
async def qr_redirect(
    short_code: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Redirect from QR code scan. Marks the click as a QR click.
    """
    # Find link by short code (case-insensitive)
    link = db.query(Link).filter(
        sql_func.lower(Link.short_code) == short_code.lower()
    ).first()

    if not link:
        from .api.links import get_404_page
        response = HTMLResponse(content=get_404_page(), status_code=404)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
        return response

    if not link.is_active:
        from .api.links import get_404_page
        response = HTMLResponse(content=get_404_page(), status_code=410)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
        return response

    # Get client info
    client_ip = get_client_ip(request)
    user_agent = request.headers.get('user-agent', '')[:512]
    referer = request.headers.get('referer', '')[:512]

    # Get geo data
    geo = get_geo_data(client_ip)

    # Check if unique visitor
    is_unique, user_agent_hash = check_unique_visitor(db, link.id, client_ip, user_agent)

    # Record click statistics with QR flag
    click = Click(
        link_id=link.id,
        ip_address=client_ip,
        user_agent=user_agent,
        referer=referer,
        country_code=geo.country_code,
        country_name=geo.country_name,
        city=geo.city,
        is_unique=is_unique,
        is_qr_click=True  # Mark as QR click
    )
    db.add(click)
    db.flush()

    # Record unique visitor if new
    if is_unique:
        record_unique_visitor(db, link.id, client_ip, user_agent_hash, click.id)
        link.unique_clicks_count += 1

    # Increment click counter
    link.clicks_count += 1

    db.commit()

    # Redirect to original URL
    response = RedirectResponse(url=link.original_url, status_code=302)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    return response


# Redirect endpoint (must be last to not conflict with other routes)
app.get("/{short_code}")(redirect_to_url)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
