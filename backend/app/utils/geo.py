import re
import hashlib
from functools import lru_cache
from typing import Optional, Tuple
from datetime import date

import httpx

# Private IP patterns
PRIVATE_IP_PATTERNS = [
    re.compile(r'^127\.'),  # Loopback
    re.compile(r'^10\.'),  # Class A private
    re.compile(r'^172\.(1[6-9]|2[0-9]|3[0-1])\.'),  # Class B private
    re.compile(r'^192\.168\.'),  # Class C private
    re.compile(r'^169\.254\.'),  # Link-local
    re.compile(r'^::1$'),  # IPv6 loopback
    re.compile(r'^fc00:', re.IGNORECASE),  # IPv6 unique local
    re.compile(r'^fe80:', re.IGNORECASE),  # IPv6 link-local
]


def is_private_ip(ip: str) -> bool:
    """Check if IP address is private/local"""
    if not ip:
        return True
    for pattern in PRIVATE_IP_PATTERNS:
        if pattern.match(ip):
            return True
    return False


def hash_user_agent(user_agent: str) -> str:
    """Create SHA256 hash of user agent string"""
    if not user_agent:
        user_agent = ""
    return hashlib.sha256(user_agent.encode('utf-8')).hexdigest()


class GeoData:
    """Container for geo data"""
    def __init__(self, country_code: Optional[str] = None,
                 country_name: Optional[str] = None,
                 city: Optional[str] = None):
        self.country_code = country_code
        self.country_name = country_name
        self.city = city


# LRU cache for geo data (max 10000 entries)
@lru_cache(maxsize=10000)
def _get_geo_data_cached(ip: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Get geo data from ip-api.com with caching.
    Returns tuple: (country_code, country_name, city)
    """
    if is_private_ip(ip):
        return (None, None, None)

    try:
        with httpx.Client(timeout=2.0) as client:
            response = client.get(
                f"http://ip-api.com/json/{ip}",
                params={"fields": "status,country,countryCode,city"}
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    return (
                        data.get("countryCode"),
                        data.get("country"),
                        data.get("city")
                    )
    except Exception:
        pass

    return (None, None, None)


def get_geo_data(ip: str) -> GeoData:
    """
    Get geo data for IP address with LRU caching.
    Uses ip-api.com (free, 45 req/min limit).
    """
    country_code, country_name, city = _get_geo_data_cached(ip)
    return GeoData(
        country_code=country_code,
        country_name=country_name,
        city=city
    )


def check_unique_visitor(db, link_id: int, ip_address: str, user_agent: str) -> Tuple[bool, str]:
    """
    Check if visitor is unique for today.
    Returns: (is_unique, user_agent_hash)
    """
    from ..models import UniqueVisitor

    user_agent_hash = hash_user_agent(user_agent)
    today = date.today()

    existing = db.query(UniqueVisitor).filter(
        UniqueVisitor.link_id == link_id,
        UniqueVisitor.ip_address == ip_address,
        UniqueVisitor.user_agent_hash == user_agent_hash,
        UniqueVisitor.visit_date == today
    ).first()

    return (existing is None, user_agent_hash)


def record_unique_visitor(db, link_id: int, ip_address: str, user_agent_hash: str,
                          click_id: int) -> None:
    """Record a unique visitor entry"""
    from ..models import UniqueVisitor

    visitor = UniqueVisitor(
        link_id=link_id,
        ip_address=ip_address,
        user_agent_hash=user_agent_hash,
        visit_date=date.today(),
        first_click_id=click_id
    )
    db.add(visitor)
