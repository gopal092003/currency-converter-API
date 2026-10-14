
from __future__ import annotations

from app.modules.rate_limiting.policies import (
    RateLimitDecision,
    RateLimitPolicy,
    RateLimitScope,
)
from app.modules.rate_limiting.storage import RateLimitStorage


class RateLimitService:
    def __init__(self, storage: RateLimitStorage) -> None:
        self.storage = storage

    async def check(
        self,
        *,
        policy: RateLimitPolicy,
        identity: str,
    ) -> RateLimitDecision:
        if not identity:
            raise ValueError("Rate-limit identity cannot be empty")

        counter_key = (
            f"rate-limit:v1:{policy.scope.value}:"
            f"{policy.name}:{identity}"
        )

        result = await self.storage.increment(
            counter_key,
            policy.window_seconds,
        )

        allowed = result.count <= policy.limit
        remaining = max(0, policy.limit - result.count)
        retry_after = (
            result.reset_after_seconds if not allowed else 0
        )

        return RateLimitDecision(
            allowed=allowed,
            limit=policy.limit,
            remaining=remaining,
            reset_after_seconds=result.reset_after_seconds,
            policy_name=policy.name,
            retry_after_seconds=retry_after,
        )

    async def check_request(
        self,
        *,
        ip_identity: str,
        endpoint_identity: str,
        endpoint_policy: RateLimitPolicy,
        ip_policy: RateLimitPolicy,
    ) -> tuple[RateLimitDecision, RateLimitDecision | None]:
        """Enforce IP protection first, then the endpoint-specific policy."""
        ip_decision = await self.check(
            policy=ip_policy,
            identity=ip_identity,
        )

        if not ip_decision.allowed:
            return ip_decision, None

        endpoint_decision = await self.check(
            policy=endpoint_policy,
            identity=endpoint_identity,
        )

        return endpoint_decision, ip_decision
