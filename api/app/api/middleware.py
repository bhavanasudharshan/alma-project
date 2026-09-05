"""Cross-cutting HTTP middleware: request correlation and browser hardening."""

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import Settings
from app.core.logging import request_id_var


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Give every request an id, echo it back, and log one line per request (M5).

    An inbound ``X-Request-ID`` is honoured so a trace started at the edge survives
    into these logs; otherwise one is generated.
    """

    def __init__(self, app, header: str = "X-Request-ID") -> None:
        super().__init__(app)
        self._header = header

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get(self._header) or uuid.uuid4().hex
        token = request_id_var.set(request_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)

        response.headers[self._header] = request_id
        response.headers["X-Response-Time-ms"] = f"{(time.perf_counter() - started) * 1000:.1f}"
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Baseline browser hardening for the API (SEC6).

    The API serves JSON and file downloads, never HTML, so the CSP can be maximally
    restrictive: nothing is allowed to load at all. HSTS is only sent outside local
    development, where there is no TLS to pin to.
    """

    def __init__(self, app, settings: Settings) -> None:
        super().__init__(app)
        self._is_local = settings.environment == "local"

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'"
        )
        if not self._is_local:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response
