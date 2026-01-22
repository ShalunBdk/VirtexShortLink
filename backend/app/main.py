from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from pathlib import Path

from .database import engine, Base
from .api import links, auth, admin
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

# Root endpoint - serve main page
@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main shortening page"""
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


# Redirect endpoint (must be last to not conflict with other routes)
# This is imported from links router but placed here for proper routing
from .api.links import redirect_to_url
app.get("/{short_code}")(redirect_to_url)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
