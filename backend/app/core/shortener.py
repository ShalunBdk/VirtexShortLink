import random
import string
from sqlalchemy.orm import Session
from sqlalchemy import func


# Only lowercase letters and digits for case-insensitive short codes (Base36)
CHARSET = string.ascii_lowercase + string.digits  # a-z0-9


def generate_short_code(length: int = 5, db: Session = None) -> str:
    """
    Generate a unique case-insensitive short code.

    Args:
        length: Length of the code (4 or 5 characters)
        db: Database session for uniqueness check

    Returns:
        A unique lowercase short code

    Note:
        - 4 chars: 36^4 = 1,679,616 combinations
        - 5 chars: 36^5 = 60,466,176 combinations
    """
    from ..models import Link  # Import here to avoid circular dependency

    max_attempts = 100
    attempt = 0

    while attempt < max_attempts:
        # Generate random code in lowercase
        code = ''.join(random.choices(CHARSET, k=length))

        # Check uniqueness in database
        if db:
            existing = db.query(Link).filter(
                func.lower(Link.short_code) == code.lower()
            ).first()

            if not existing:
                return code.lower()
        else:
            return code.lower()

        attempt += 1

    # If we couldn't find a unique code, increase length by 1
    if length < 6:
        return generate_short_code(length + 1, db)

    raise ValueError("Unable to generate unique short code")


def validate_custom_alias(alias: str) -> tuple[bool, str]:
    """
    Validate custom alias for short code.

    Args:
        alias: The custom alias to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not alias:
        return False, "Alias cannot be empty"

    # Check length
    if len(alias) < 3:
        return False, "Alias must be at least 3 characters"

    if len(alias) > 20:
        return False, "Alias must be at most 20 characters"

    # Only allowed characters: a-z, 0-9, hyphen
    alias_lower = alias.lower()
    allowed = set(string.ascii_lowercase + string.digits + '-')

    if not all(c in allowed for c in alias_lower):
        return False, "Alias can only contain letters, digits, and hyphens"

    # Cannot start or end with hyphen
    if alias_lower.startswith('-') or alias_lower.endswith('-'):
        return False, "Alias cannot start or end with a hyphen"

    # Reserved words
    reserved = [
        'admin', 'api', 'static', 'www', 'app', 'docs', 'redoc',
        'openapi', 'health', 'status', 'login', 'logout', 'auth'
    ]

    if alias_lower in reserved:
        return False, f"'{alias}' is a reserved word and cannot be used"

    return True, ""


def is_code_available(code: str, db: Session) -> bool:
    """
    Check if a short code is available (case-insensitive).

    Args:
        code: The short code to check
        db: Database session

    Returns:
        True if available, False otherwise
    """
    from ..models import Link

    existing = db.query(Link).filter(
        func.lower(Link.short_code) == code.lower()
    ).first()

    return existing is None
