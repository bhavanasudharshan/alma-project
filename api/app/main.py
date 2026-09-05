"""FastAPI application factory (M1: transport wiring only, no business logic)."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded

from app.api.errors import register_exception_handlers
from app.api.middleware import RequestIdMiddleware, SecurityHeadersMiddleware
from app.api.v1 import api_router
from app.core.config import Settings, get_settings
from app.core.deps import get_file_storage
from app.core.limiter import limiter
from app.core.logging import configure_logging

logger = logging.getLogger(__name__)

OPENAPI_TAGS = [
    {"name": "health", "description": "Liveness and dependency checks."},
    {"name": "auth", "description": "Attorney authentication."},
    {"name": "leads", "description": "Public lead submission and the internal intake queue."},
]


class InsecureConfiguration(RuntimeError):
    """Raised at startup when placeholder credentials survive outside local dev."""


def _assert_secure_configuration(settings: Settings) -> None:
    """Refuse to start a non-local deployment with placeholder secrets (S4).

    A warning is not enough: a deployment that ships with a known JWT key and a known
    attorney password is not degraded, it is unauthenticated. Failing loudly at boot is
    the only outcome that cannot be ignored.
    """
    insecure = settings.insecure_defaults()
    if not insecure:
        return
    raise InsecureConfiguration(
        f"Refusing to start in environment {settings.environment!r} with placeholder "
        f"credentials: {', '.join(insecure)}. Set real values."
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Prepare backing services once per process."""
    settings = app.state.settings

    if settings.uses_s3:
        # MinIO starts with no buckets; make the configured one exist before traffic.
        storage = get_file_storage()
        ensure = getattr(storage, "ensure_bucket", None)
        if ensure:
            try:
                ensure()
            except Exception:
                # Fail visibly in the log, but let the app boot: the health check and
                # the first upload will report the real problem (A1).
                logger.exception("Could not verify the object storage bucket at startup")

    yield


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the ASGI app. Accepts settings so tests can construct isolated apps."""
    settings = settings or get_settings()

    configure_logging(debug=settings.debug, json_logs=settings.log_json)
    _assert_secure_configuration(settings)

    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        openapi_url=f"{settings.api_v1_prefix}/openapi.json",
        openapi_tags=OPENAPI_TAGS,
        lifespan=lifespan,
        description=(
            "Lead intake: a public submission endpoint for prospective clients, and an "
            "authenticated queue for the attorneys who review them."
        ),
    )
    app.state.settings = settings

    # SEC1: slowapi needs its limiter and handler on the app.
    app.state.limiter = limiter

    # Middleware runs bottom-up, so request-id is added last to wrap everything below.
    app.add_middleware(SecurityHeadersMiddleware, settings=settings)
    app.add_middleware(
        CORSMiddleware,
        # S5: browser origins come from settings, never a wildcard.
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[settings.request_id_header],
    )
    app.add_middleware(RequestIdMiddleware, header=settings.request_id_header)

    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()


__all__ = ["InsecureConfiguration", "RateLimitExceeded", "app", "create_app"]
