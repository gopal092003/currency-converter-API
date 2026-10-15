from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from app.core.security import hash_api_key, is_valid_api_key_format
from app.modules.rate_limiting.policies import (
    DEFAULT_IP_POLICY,
    RateLimitDecision,
    select_endpoint_policy,
)
from app.modules.rate_limiting.service import RateLimitService

logger = logging.getLogger(__name__)

_EXEMPT_PATHS = {
    "/health/live",
    "/health/ready",
}


class RateLimitMiddleware:
    def __init__(
        self,
        app,
        *,
        service: RateLimitService,
        enabled: bool = True,
        fail_closed: bool = True,
        key_header: str = "x-api-key",
    ) -> None:
        self.app = app
        self.service = service
        self.enabled = enabled
        self.fail_closed = fail_closed
        self.key_header = key_header.lower().encode("latin-1")

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http" or not self.enabled:
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "/")

        if path in _EXEMPT_PATHS or path == "/metrics":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        client = scope.get("client")
        ip = client[0] if client else "unknown"

        # Do not trust X-Forwarded-For unless a trusted-proxy layer has
        # explicitly validated it. A client can otherwise spoof this header.
        ip_identity = hashlib.sha256(ip.encode()).hexdigest()

        endpoint_policy = select_endpoint_policy(path)
        supplied_key = headers.get(self.key_header, b"").decode("latin-1")

        # If an earlier authentication middleware has populated a validated
        # API-key record, prefer its stable database ID.
        state: dict[str, Any] = scope.setdefault("state", {})
        authenticated_key = state.get("api_key")

        if (
            authenticated_key is not None
            and getattr(authenticated_key, "id", None) is not None
        ):
            endpoint_identity = f"key-id:{authenticated_key.id}"
        elif is_valid_api_key_format(supplied_key):
            # A hashed secret is not sent to Redis or logged. This bucket
            # supplements IP throttling; it is not proof of authentication.
            endpoint_identity = f"key-hash:{hash_api_key(supplied_key)}"
        else:
            endpoint_identity = f"ip-fallback:{ip_identity}"

        try:
            decision, ip_decision = await self.service.check_request(
                ip_identity=ip_identity,
                endpoint_identity=endpoint_identity,
                endpoint_policy=endpoint_policy,
                ip_policy=DEFAULT_IP_POLICY,
            )
        except Exception:
            logger.exception("Rate-limit storage operation failed")

            if self.fail_closed:
                await self._send_json(
                    scope,
                    receive,
                    send,
                    status_code=503,
                    body={
                        "success": False,
                        "error": {
                            "code": "RATE_LIMIT_STORAGE_UNAVAILABLE",
                            "message": "Request protection is temporarily unavailable.",
                        },
                    },
                    headers=[(b"retry-after", b"1")],
                )
                return

            await self.app(scope, receive, send)
            return

        # If the IP limit is exceeded, check_request returns that decision
        # and leaves ip_decision as None.
        if not decision.allowed:
            await self._reject(scope, receive, send, decision)
            return

        response_headers = [
            (
                b"x-ratelimit-limit",
                str(decision.limit).encode(),
            ),
            (
                b"x-ratelimit-remaining",
                str(decision.remaining).encode(),
            ),
            (
                b"x-ratelimit-reset",
                str(decision.reset_after_seconds).encode(),
            ),
        ]

        async def send_with_rate_headers(message) -> None:
            if message["type"] == "http.response.start":
                message = dict(message)
                existing = list(message.get("headers", []))
                existing_names = {name.lower() for name, _ in existing}
                existing.extend(
                    (name, value)
                    for name, value in response_headers
                    if name not in existing_names
                )
                message["headers"] = existing

            await send(message)

        await self.app(scope, receive, send_with_rate_headers)

    async def _reject(
        self,
        scope,
        receive,
        send,
        decision: RateLimitDecision,
    ) -> None:
        retry_after = max(1, decision.retry_after_seconds)

        await self._send_json(
            scope,
            receive,
            send,
            status_code=429,
            body={
                "success": False,
                "error": {
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": "Too many requests. Please retry later.",
                    "details": {
                        "policy": decision.policy_name,
                        "limit": decision.limit,
                        "remaining": decision.remaining,
                        "retry_after_seconds": retry_after,
                    },
                },
            },
            headers=[
                (b"retry-after", str(retry_after).encode()),
                (
                    b"x-ratelimit-limit",
                    str(decision.limit).encode(),
                ),
                (b"x-ratelimit-remaining", b"0"),
                (
                    b"x-ratelimit-reset",
                    str(decision.reset_after_seconds).encode(),
                ),
            ],
        )

    @staticmethod
    async def _send_json(
        scope,
        receive,
        send,
        *,
        status_code: int,
        body: dict[str, Any],
        headers: list[tuple[bytes, bytes]] | None = None,
    ) -> None:
        payload = json.dumps(body, separators=(",", ":")).encode()
        response_headers = [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(payload)).encode()),
            *(headers or []),
        ]

        await send(
            {
                "type": "http.response.start",
                "status": status_code,
                "headers": response_headers,
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": payload,
            }
        )
