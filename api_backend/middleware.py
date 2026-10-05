"""Request correlation and terminal logs for API requests."""

import logging
from time import perf_counter
from uuid import uuid4

from utils.logging_utils import REQUEST_ID, log_error, log_event


class RequestLoggingMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        request_id = uuid4().hex
        scope.setdefault("state", {})["request_id"] = request_id
        token = REQUEST_ID.set(request_id)
        started = perf_counter()
        status = None

        async def send_response(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                message = {
                    **message,
                    "headers": [
                        *message.get("headers", []),
                        (b"x-request-id", request_id.encode("ascii")),
                    ],
                }
            await send(message)

        try:
            await self.app(scope, receive, send_response)
        except Exception as exc:
            route = getattr(scope.get("route"), "path", "unmatched")
            log_error(
                exc, event="api_unhandled_error", method=scope["method"], route=route
            )
            raise
        finally:
            if status is not None:
                route = getattr(scope.get("route"), "path", "unmatched")
                log_event(
                    "api_request_failed" if status >= 400 else "api_request_completed",
                    level=logging.WARNING if status >= 400 else logging.INFO,
                    method=scope["method"],
                    route=route,
                    status_code=status,
                    duration_ms=round((perf_counter() - started) * 1000, 2),
                )
            REQUEST_ID.reset(token)
