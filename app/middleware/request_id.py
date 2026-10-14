
"""Request ID middleware."""

import re
import uuid
from collections.abc import Iterable

from app.core.config import settings


_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,128}$")


class RequestIDMiddleware:
    """Generate or propagate a safe request ID using ASGI middleware."""

    def __init__(
        self,
        app,
        header_name: str | None = None,
    ) -> None:
        self.app = app
        self.header_name = (
            header_name or settings.request_id_header
        )
        self.header_name_bytes = self.header_name.lower().encode("ascii")

    @staticmethod
    def _get_header(
        headers: Iterable[tuple[bytes, bytes]],
        target: bytes,
    ) -> str | None:
        for name, value in headers:
            if name.lower() == target:
                try:
                    return value.decode("ascii")
                except UnicodeDecodeError:
                    return None
        return None

    def _resolve_request_id(self, value: str | None) -> str:
        if value and _REQUEST_ID_PATTERN.fullmatch(value):
            return value

        return str(uuid.uuid4())

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = self._resolve_request_id(
            self._get_header(
                scope.get("headers", []),
                self.header_name_bytes,
            )
        )

        # ASGI state is shared with Starlette's Request.state.
        scope.setdefault("state", {})["request_id"] = request_id

        async def send_with_request_id(message) -> None:
            if message["type"] == "http.response.start":
                headers = [
                    (name, value)
                    for name, value in message.get("headers", [])
                    if name.lower() != self.header_name_bytes
                ]
                headers.append(
                    (
                        self.header_name_bytes,
                        request_id.encode("ascii"),
                    )
                )
                message = {**message, "headers": headers}

            await send(message)

        await self.app(scope, receive, send_with_request_id)
