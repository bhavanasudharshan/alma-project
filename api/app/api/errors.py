"""HTTP error mapping. The only module that turns domain errors into status codes (M6).

Every failure leaves the API as ``{"detail": str, "code": str}`` so the web client can
branch on a stable code, and no stack trace ever reaches a client.
"""

import logging

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.services.exceptions import (
    AlreadyInState,
    DomainError,
    InvalidCredentials,
    InvalidTransition,
    LeadNotFound,
    ResumeTooLarge,
    StorageUnavailable,
    UnknownAssignee,
    UnsupportedResumeType,
)

logger = logging.getLogger(__name__)

# Domain vocabulary -> transport. Adding an error means adding one row here.
STATUS_BY_ERROR: dict[type[DomainError], int] = {
    LeadNotFound: status.HTTP_404_NOT_FOUND,
    InvalidTransition: status.HTTP_409_CONFLICT,
    AlreadyInState: status.HTTP_409_CONFLICT,
    UnsupportedResumeType: status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
    ResumeTooLarge: status.HTTP_413_CONTENT_TOO_LARGE,
    StorageUnavailable: status.HTTP_503_SERVICE_UNAVAILABLE,
    InvalidCredentials: status.HTTP_401_UNAUTHORIZED,
    UnknownAssignee: status.HTTP_422_UNPROCESSABLE_CONTENT,
}

_STATUS_CODE_FALLBACK = {
    status.HTTP_401_UNAUTHORIZED: "not_authenticated",
    status.HTTP_403_FORBIDDEN: "forbidden",
    status.HTTP_404_NOT_FOUND: "not_found",
    status.HTTP_405_METHOD_NOT_ALLOWED: "method_not_allowed",
}


class ApiHTTPError(HTTPException):
    """An ``HTTPException`` that also carries a machine-readable code."""

    def __init__(
        self,
        status_code: int,
        detail: str,
        code: str,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.code = code


def _envelope(status_code: int, detail: str, code: str, headers=None) -> JSONResponse:
    """Build the single response shape used for every error."""
    return JSONResponse(
        status_code=status_code,
        content={"detail": detail, "code": code},
        headers=headers,
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach the global handlers to ``app``."""

    @app.exception_handler(DomainError)
    async def _domain_error(_: Request, exc: DomainError) -> JSONResponse:
        status_code = STATUS_BY_ERROR.get(type(exc), status.HTTP_400_BAD_REQUEST)
        headers = {"WWW-Authenticate": "Bearer"} if status_code == 401 else None
        return _envelope(status_code, exc.detail, exc.code, headers)

    @app.exception_handler(ApiHTTPError)
    async def _api_http_error(_: Request, exc: ApiHTTPError) -> JSONResponse:
        return _envelope(exc.status_code, str(exc.detail), exc.code, exc.headers)

    @app.exception_handler(HTTPException)
    async def _http_error(_: Request, exc: HTTPException) -> JSONResponse:
        code = _STATUS_CODE_FALLBACK.get(exc.status_code, "http_error")
        return _envelope(exc.status_code, str(exc.detail), code, exc.headers)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        # Field-level detail is useful to the form and leaks nothing sensitive.
        first = exc.errors()[0] if exc.errors() else {}
        location = ".".join(str(part) for part in first.get("loc", ())[1:])
        message = first.get("msg", "Invalid request.")
        detail = f"{location}: {message}" if location else message
        return _envelope(status.HTTP_422_UNPROCESSABLE_CONTENT, detail, "validation_error")

    @app.exception_handler(RateLimitExceeded)
    async def _rate_limited(_: Request, exc: RateLimitExceeded) -> JSONResponse:
        """SEC1: 429 in the standard envelope, with Retry-After so clients can back off."""
        # limits models a window as (multiples x granularity), e.g. 10 minutes.
        item = exc.limit.limit
        window = item.GRANULARITY.seconds * item.multiples
        retry_after = str(window)
        return _envelope(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Too many requests. Please wait and try again.",
            "rate_limited",
            {"Retry-After": retry_after},
        )

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
        # Logged in full server-side, opaque to the client: never leak a traceback.
        logger.exception("Unhandled error", exc_info=exc)
        return _envelope(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Internal server error.",
            "internal_error",
        )
