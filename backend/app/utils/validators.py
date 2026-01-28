from urllib.parse import urlparse
import re


def is_valid_url(url: str) -> tuple[bool, str]:
    """
    Validate if a URL is valid and safe.

    Args:
        url: The URL to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not url or len(url) < 1:
        return False, "URL cannot be empty"

    if len(url) > 2048:
        return False, "URL is too long (max 2048 characters)"

    try:
        result = urlparse(url)

        # Must have scheme and netloc
        if not all([result.scheme, result.netloc]):
            return False, "Invalid URL format"

        # Only http and https
        if result.scheme not in ['http', 'https']:
            return False, "Only HTTP and HTTPS URLs are allowed"

        # Check for suspicious/blocked domains
        suspicious_domains = [
            'localhost',
            '127.0.0.1',
            '0.0.0.0',
            '::1',
            '10.',  # Private network
            '192.168.',  # Private network
            '172.16.',  # Private network
        ]

        netloc_lower = result.netloc.lower()
        for suspicious in suspicious_domains:
            if suspicious in netloc_lower:
                return False, "Internal/private URLs are not allowed"

        return True, ""

    except Exception as e:
        return False, f"Invalid URL: {str(e)}"


def is_spam_url(url: str) -> bool:
    """
    Check if URL contains spam keywords.

    Args:
        url: The URL to check

    Returns:
        True if spam detected, False otherwise
    """
    # Common spam keywords (can be extended)
    spam_keywords = [
        'porn', 'xxx', 'adult', 'sex',
        'casino', 'gambling', 'poker',
        'viagra', 'cialis', 'pharmacy',
        'bitcoin', 'crypto', 'lottery', 'prize',
        'click-here', 'free-money', 'earn-money'
    ]

    url_lower = url.lower()

    # Check if any spam keyword is in URL
    for keyword in spam_keywords:
        if keyword in url_lower:
            return True

    return False


def is_ip_blacklisted(ip: str, db) -> bool:
    """
    Check if an IP address is blacklisted.

    Args:
        ip: IP address to check
        db: Database session

    Returns:
        True if blacklisted, False otherwise
    """
    from ..models import IPBlacklist

    if not ip:
        return False

    blocked = db.query(IPBlacklist).filter(
        IPBlacklist.ip_address == ip
    ).first()

    return blocked is not None


def get_client_ip(request) -> str:
    """
    Get client IP address from request.

    Args:
        request: FastAPI request object

    Returns:
        Client IP address
    """
    # Check for X-Forwarded-For header (if behind proxy)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Take the first IP in the chain
        return forwarded.split(",")[0].strip()

    # Otherwise use client.host
    return request.client.host if request.client else "unknown"


def parse_user_agent_os(user_agent: str) -> str:
    """
    Parse user agent string to detect operating system.

    Args:
        user_agent: User-Agent header value

    Returns:
        OS name (Windows, macOS, Linux, Android, iOS, etc.)
    """
    if not user_agent:
        return "Unknown"

    ua_lower = user_agent.lower()

    # Mobile OS detection (check first as they may contain desktop OS strings)
    if 'iphone' in ua_lower or 'ipad' in ua_lower or 'ipod' in ua_lower:
        return "iOS"
    if 'android' in ua_lower:
        return "Android"
    if 'windows phone' in ua_lower:
        return "Windows Phone"

    # Desktop OS detection
    if 'windows nt 10' in ua_lower:
        return "Windows 10/11"
    if 'windows nt 6.3' in ua_lower:
        return "Windows 8.1"
    if 'windows nt 6.2' in ua_lower:
        return "Windows 8"
    if 'windows nt 6.1' in ua_lower:
        return "Windows 7"
    if 'windows' in ua_lower:
        return "Windows"

    if 'macintosh' in ua_lower or 'mac os x' in ua_lower:
        return "macOS"

    if 'linux' in ua_lower:
        if 'ubuntu' in ua_lower:
            return "Ubuntu"
        if 'fedora' in ua_lower:
            return "Fedora"
        return "Linux"

    if 'cros' in ua_lower:
        return "Chrome OS"

    # Bots
    if 'bot' in ua_lower or 'crawler' in ua_lower or 'spider' in ua_lower:
        return "Bot"

    return "Other"
