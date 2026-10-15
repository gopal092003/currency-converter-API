from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class RateLimitScope(StrEnum):
    IP = "ip"
    API_KEY = "api_key"
    GLOBAL = "global"


@dataclass(frozen=True, slots=True)
class RateLimitPolicy:
    name: str
    limit: int
    window_seconds: int
    scope: RateLimitScope = RateLimitScope.API_KEY

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Policy name cannot be empty")
        if self.limit < 1:
            raise ValueError("limit must be at least 1")
        if self.window_seconds < 1:
            raise ValueError("window_seconds must be at least 1")


@dataclass(frozen=True, slots=True)
class RateLimitDecision:
    allowed: bool
    limit: int
    remaining: int
    reset_after_seconds: int
    policy_name: str
    retry_after_seconds: int = 0


# Defaults are deliberately conservative examples. Tune these to your
# expected workload and any provider/API contract requirements.
DEFAULT_IP_POLICY = RateLimitPolicy(
    name="ip_default",
    limit=120,
    window_seconds=60,
    scope=RateLimitScope.IP,
)

DEFAULT_API_KEY_POLICY = RateLimitPolicy(
    name="api_key_default",
    limit=300,
    window_seconds=60,
    scope=RateLimitScope.API_KEY,
)

CONVERSION_POLICY = RateLimitPolicy(
    name="conversion",
    limit=60,
    window_seconds=60,
    scope=RateLimitScope.API_KEY,
)

READ_POLICY = RateLimitPolicy(
    name="read",
    limit=180,
    window_seconds=60,
    scope=RateLimitScope.API_KEY,
)

# Paths are relative to the mounted API router, so these match
# /api/v1/convert/ and /api/v1/rates/ after path normalization.
ENDPOINT_POLICIES: tuple[tuple[str, RateLimitPolicy], ...] = (
    ("/api/v1/convert", CONVERSION_POLICY),
    ("/api/v1/rates", READ_POLICY),
    ("/api/v1/currencies", READ_POLICY),
)


def select_endpoint_policy(path: str) -> RateLimitPolicy:
    normalized = path.rstrip("/") or "/"

    for prefix, policy in ENDPOINT_POLICIES:
        if normalized == prefix or normalized.startswith(prefix + "/"):
            return policy

    return DEFAULT_API_KEY_POLICY
