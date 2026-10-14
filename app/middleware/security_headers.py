
"""Security headers middleware."""

from app.core.config import settings


class SecurityHeadersMiddleware:
    """Apply baseline security headers to HTTP responses."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_security_headers(message) -> None:
            if message["type"] == "http.response.start":
                headers = [
                    (name, value)
                    for name, value in message.get("headers", [])
                    if name.lower() not in {
                        b"x-content-type-options",
                        b"x-frame-options",
                        b"referrer-policy",
                        b"permissions-policy",
                        b"strict-transport-security",
                    }
                ]

                headers.extend(
                    [
                        (b"x-content-type-options", b"nosniff"),
                        (b"x-frame-options", b"DENY"),
                        (b"referrer-policy", b"no-referrer"),
                        (
                            b"permissions-policy",
                            b"camera=(), microphone=(), geolocation=()",
                        ),
                    ]
                )

                is_production = settings.app_env in {
                    "staging",
                    "production",
                }
                is_https = scope.get("scheme") == "https"

                if is_production and is_https:
                    headers.append(
                        (
                            b"strict-transport-security",
                            b"max-age=31536000",
                        )
                    )

                message = {**message, "headers": headers}

            await send(message)

        await self.app(scope, receive, send_with_security_headers)
