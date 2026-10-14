
from __future__ import annotations

import hashlib
import hmac
import re
import secrets

from app.core.config import settings

# The prefix is stored separately for efficient key lookup.
# The secret portion is returned only once to the client.
API_KEY_PREFIX_LENGTH = 12
API_KEY_PATTERN = re.compile(r"^cc_(live|test)_([A-Za-z0-9_-]{32,})$")


def _pepper() -> bytes:
    """Return the server-side secret used when hashing API keys."""
    value = settings.api_key_pepper

    if value is None:
        raise RuntimeError(
            "API_KEY_PEPPER must be configured before API-key "
            "authentication or creation is enabled."
        )

    if hasattr(value, "get_secret_value"):
        value = value.get_secret_value()

    if not isinstance(value, str):
        value = str(value)

    return value.encode("utf-8")


def generate_api_key(*, environment: str = "live") -> str:
    """Generate a high-entropy API key.

    The complete key must be shown to the caller only once.
    """
    if environment not in {"live", "test"}:
        raise ValueError("environment must be 'live' or 'test'")

    secret = secrets.token_urlsafe(32)
    return f"cc_{environment}_{secret}"


def get_api_key_prefix(raw_key: str) -> str:
    """Extract the non-secret lookup prefix from a well-formed key."""
    if not isinstance(raw_key, str):
        raise ValueError("API key must be a string")

    if not API_KEY_PATTERN.fullmatch(raw_key):
        raise ValueError("Malformed API key")

    return raw_key[:API_KEY_PREFIX_LENGTH]


def hash_api_key(raw_key: str) -> str:
    """Return a deterministic HMAC-SHA-256 digest for database storage."""
    if not isinstance(raw_key, str) or not API_KEY_PATTERN.fullmatch(raw_key):
        raise ValueError("Malformed API key")

    return hmac.new(
        _pepper(),
        raw_key.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verify_api_key(raw_key: str, stored_hash: str) -> bool:
    """Verify a supplied key without storing or comparing raw secrets."""
    try:
        candidate_hash = hash_api_key(raw_key)
    except (ValueError, RuntimeError):
        return False

    return hmac.compare_digest(candidate_hash, stored_hash)


def is_valid_api_key_format(raw_key: str) -> bool:
    """Check key syntax without checking whether the key exists."""
    return isinstance(raw_key, str) and bool(
        API_KEY_PATTERN.fullmatch(raw_key)
    )
