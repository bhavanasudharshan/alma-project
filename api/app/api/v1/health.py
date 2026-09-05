"""Health router (M5)."""

import logging

from fastapi import APIRouter, Response, status
from sqlalchemy import text

from app.core.deps import DbDep

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    summary="Liveness and dependency check",
    responses={
        200: {"description": "The app is serving and the database answers"},
        503: {"description": "The database is unreachable"},
    },
)
def health(response: Response, db: DbDep) -> dict[str, str]:
    """Report app liveness plus database connectivity (M5).

    A health check that only proves the process is running will happily report green
    while every request 500s, so this actually touches the database.
    """
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Health check could not reach the database")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "degraded", "database": "unreachable"}

    return {"status": "ok", "database": "ok"}
