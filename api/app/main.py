"""FastAPI application factory (M1: transport wiring only, no business logic)."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import register_exception_handlers
from app.api.v1 import api_router
from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the ASGI app. Accepts settings so tests can construct isolated apps."""
    settings = settings or get_settings()

    logging.basicConfig(
        level=logging.DEBUG if settings.debug else logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )

    # S4: refuse to let placeholder credentials leave a developer machine unnoticed.
    if insecure := settings.insecure_defaults():
        logger.warning(
            "Running in environment %r with placeholder credentials still set: %s. "
            "Set real values before deploying.",
            settings.environment,
            ", ".join(insecure),
        )

    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        openapi_url=f"{settings.api_v1_prefix}/openapi.json",
    )

    # S5: browser origins come from settings, never a wildcard.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()
