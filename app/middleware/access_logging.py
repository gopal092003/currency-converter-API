"""HTTP access logging middleware."""

import logging
import time

logger = logging.getLogger("app.access")


class AccessLoggingMiddleware:
    """Log HTTP request summaries without sensitive payloads."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start_time = time.perf_counter()
        status_code = 500
        response_started = False

        method = scope.get("method", "UNKNOWN")
        path = scope.get("path", "/")
        request_id = scope.get("state", {}).get("request_id")

        async def send_with_logging(message) -> None:
            nonlocal status_code, response_started

            if message["type"] == "http.response.start":
                status_code = message["status"]
                response_started = True

            await send(message)

        try:
            await self.app(scope, receive, send_with_logging)
        except Exception:
            duration_ms = round(
                (time.perf_counter() - start_time) * 1000,
                2,
            )

            logger.exception(
                "HTTP request failed",
                extra={
                    "request_id": request_id,
                    "http_method": method,
                    "http_path": path,
                    "http_status_code": status_code,
                    "duration_ms": duration_ms,
                    "response_started": response_started,
                },
            )
            raise
        else:
            duration_ms = round(
                (time.perf_counter() - start_time) * 1000,
                2,
            )

            log_method = (
                logger.warning
                if status_code >= 500
                else logger.info
                if status_code >= 400
                else logger.info
            )

            log_method(
                "HTTP request completed",
                extra={
                    "request_id": request_id,
                    "http_method": method,
                    "http_path": path,
                    "http_status_code": status_code,
                    "duration_ms": duration_ms,
                },
            )
