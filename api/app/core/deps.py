"""Dependency wiring: the one place adapters are chosen from settings (M4/E2)."""

import logging
from collections.abc import Iterator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.api.errors import ApiHTTPError
from app.core.config import Settings, get_settings
from app.core.security import AttorneyDirectory, decode_token
from app.db.session import get_db
from app.repositories.lead_repo import LeadRepository
from app.services.email.base import EmailService
from app.services.email.console import ConsoleEmailService
from app.services.email.resend import ResendEmailService
from app.services.exceptions import InvalidCredentials
from app.services.lead_service import LeadService
from app.services.storage.base import FileStorage
from app.services.storage.local import LocalDiskStorage
from app.services.storage.s3 import S3Storage

logger = logging.getLogger(__name__)

SettingsDep = Annotated[Settings, Depends(get_settings)]
DbDep = Annotated[Session, Depends(get_db)]

# Auto-error off so a missing header produces our own {detail, code} envelope (M6).
_bearer = HTTPBearer(auto_error=False)


# Adapters are process-wide singletons: Settings is not hashable, so these take no
# arguments and read the cached settings object themselves.
@lru_cache
def get_email_service() -> EmailService:
    """Resend when an API key is configured, console otherwise (M4).

    Selection is by configuration alone -- no service or router knows which one it got.
    """
    settings = get_settings()
    if settings.uses_resend:
        logger.info("Email adapter: Resend (from=%s)", settings.email_from)
        return ResendEmailService(settings)
    logger.info("Email adapter: console (set RESEND_API_KEY to send for real)")
    return ConsoleEmailService()


@lru_cache
def get_file_storage() -> FileStorage:
    """S3/MinIO when object storage is configured, local disk otherwise (M4/E2)."""
    settings = get_settings()
    if settings.uses_s3:
        logger.info(
            "Storage adapter: S3 (bucket=%s endpoint=%s)",
            settings.s3_bucket,
            settings.s3_endpoint_url or "aws",
        )
        return S3Storage(settings)
    logger.info("Storage adapter: local disk (%s)", settings.upload_path)
    return LocalDiskStorage(root=settings.upload_path)


@lru_cache
def get_attorney_directory() -> AttorneyDirectory:
    """Hash every roster password once per process, not per request (S4)."""
    settings = get_settings()
    directory = AttorneyDirectory(settings.roster)
    logger.info("Attorney roster: %d account(s)", len(directory.emails))
    return directory


def get_lead_service(
    db: DbDep,
    settings: SettingsDep,
    storage: Annotated[FileStorage, Depends(get_file_storage)],
    email: Annotated[EmailService, Depends(get_email_service)],
) -> Iterator[LeadService]:
    """Build a request-scoped :class:`LeadService` over a single DB session."""
    yield LeadService(
        db=db,
        repo=LeadRepository(db),
        storage=storage,
        email=email,
        settings=settings,
    )


def current_attorney(
    settings: SettingsDep,
    directory: Annotated[AttorneyDirectory, Depends(get_attorney_directory)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)] = None,
) -> str:
    """Authenticate the bearer token and return the attorney's email (S1).

    Every internal route depends on this; there is no anonymous path to lead data.
    """
    unauthorized = ApiHTTPError(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated.",
        code="not_authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None or not credentials.credentials:
        raise unauthorized

    try:
        claims = decode_token(credentials.credentials, settings)
    except InvalidCredentials as exc:
        raise unauthorized from exc

    subject = claims.get("sub")
    # A token signed for anyone other than the seeded attorney is not usable here.
    if not subject or not directory.is_known(subject):
        raise unauthorized

    return subject


AttorneyDep = Annotated[str, Depends(current_attorney)]
LeadServiceDep = Annotated[LeadService, Depends(get_lead_service)]
