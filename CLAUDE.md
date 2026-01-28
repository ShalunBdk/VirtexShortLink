# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Virtex Food Short Links - A corporate URL shortening service with admin panel. FastAPI backend (Python) with vanilla JavaScript frontend. SQLite database with WAL mode.

## Development Commands

```bash
# Install dependencies
cd backend && pip install -r requirements.txt

# Initialize database (creates default admin user)
cd backend && python init_db.py

# Run development server
cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Docker deployment
docker-compose up -d
```

**Default admin credentials:** admin / admin123

**Access points:**
- Main page: http://localhost:8000
- Admin panel: http://localhost:8000/admin
- API docs: http://localhost:8000/docs

## Architecture

### Backend Structure (`backend/app/`)
- `main.py` - FastAPI app entry point, middleware setup, static file mounting
- `config.py` - Pydantic settings (env vars: DATABASE_URL, SECRET_KEY, BASE_URL, RATE_LIMIT_*)
- `database.py` - SQLAlchemy engine/session with WAL mode
- `api/` - Route handlers (auth.py, admin.py, links.py)
- `models/` - SQLAlchemy models (link, user, click, unique_visitor, blacklist)
- `schemas/` - Pydantic validation schemas
- `core/security.py` - JWT auth, password hashing (bcrypt)
- `core/shortener.py` - Short code generation (Base36, 5 chars)
- `utils/validators.py` - URL validation, spam detection, IP checks
- `utils/geo.py` - Geolocation lookups with LRU cache

### Key Request Flows
1. **POST /api/shorten** - Creates short link with rate limiting (10/hour), spam check, duplicate detection
2. **GET /{short_code}** - Case-insensitive lookup, records click analytics with geolocation, 302 redirect
3. **Admin endpoints** - JWT protected via OAuth2PasswordBearer, require `Authorization: Bearer <token>`

### Database Models
- `links` - short_code (indexed, case-insensitive), original_url, clicks_count, unique_clicks_count, is_active
- `clicks` - link_id FK, IP, user_agent, referer, country, city, is_unique
- `unique_visitors` - link_id, IP + user_agent hash for unique tracking

### Frontend (`frontend/`)
Static HTML/JS served by FastAPI. Admin panel uses embedded JS/CSS with JWT auth stored in localStorage.

## Important Implementation Details

- **Case-insensitive codes**: All short codes stored/queried as lowercase via `func.lower()`
- **Reserved words**: 'admin', 'api', 'static', 'www', 'app', 'docs', 'redoc', 'openapi', 'health', 'status', 'login', 'logout', 'auth'
- **Custom aliases**: 3-20 chars, alphanumeric + hyphens only
- **Duplicate URLs**: Returns existing short code instead of creating new
- **Rate limiting**: SlowAPI at route level, respects X-Forwarded-For
- **Geolocation**: External API via httpx, cached with 10,000 entry LRU

## Environment Variables

```
DATABASE_URL=sqlite:///./shortlinks.db
SECRET_KEY=<change-in-production>
BASE_URL=https://vrxf.ru
SHORT_CODE_LENGTH=5
RATE_LIMIT_PER_HOUR=10
RATE_LIMIT_PER_DAY=50
```
