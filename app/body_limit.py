"""Bound the raw bytes accepted by unauthenticated local-demo endpoints.

ASGI-level buffering checks both declared and streamed body sizes *before*
FastAPI parses JSON or invokes the route. This is a memory bound per request,
not authentication, concurrency control, or protection from slow clients.
"""

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

_MAX_DEMO_BODY_BYTES = 1024 * 1024
_DEMO_PATHS = frozenset({"/v1/ingest", "/v1/resolve"})


class DemoBodyLimitMiddleware:
    """Reject oversized demo bodies without processing partial ingestion batches."""

    def __init__(self, app: ASGIApp, max_body_bytes: int = _MAX_DEMO_BODY_BYTES) -> None:
        if isinstance(max_body_bytes, bool) or not isinstance(max_body_bytes, int) or max_body_bytes < 1:
            raise ValueError("max_body_bytes must be positive")
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("path") not in _DEMO_PATHS:
            await self.app(scope, receive, send)
            return

        lengths = [
            value
            for name, value in scope.get("headers", [])
            if name.lower() == b"content-length"
        ]
        if len(lengths) > 1 or (lengths and not lengths[0].isdigit()):
            await JSONResponse(
                {"detail": "Invalid Content-Length"}, status_code=400
            )(scope, receive, send)
            return
        if lengths and int(lengths[0]) > self.max_body_bytes:
            await self._too_large(scope, receive, send)
            return

        buffered = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            if message["type"] != "http.request":
                continue
            chunk = message.get("body", b"")
            if len(buffered) + len(chunk) > self.max_body_bytes:
                await self._too_large(scope, receive, send)
                return
            buffered.extend(chunk)
            if not message.get("more_body", False):
                break

        delivered = False

        async def replay_body() -> Message:
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": bytes(buffered), "more_body": False}
            return await receive()

        await self.app(scope, replay_body, send)

    async def _too_large(self, scope: Scope, receive: Receive, send: Send) -> None:
        await JSONResponse(
            {"detail": "Demo request body exceeds 1 MiB"}, status_code=413
        )(scope, receive, send)
