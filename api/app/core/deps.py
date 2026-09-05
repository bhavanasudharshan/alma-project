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
from app.services.exceptions import InvalidCredentials
from app.services.lead_service import LeadService
from app.services.storage.base import FileStorage
from app.services.storage.local import LocalDiskStorage

logger = logging.getLogger(__name__)

SettingsDep = Annotated[Settings, Depends(get_settings)]
DbDep = Annotated[Session, Depends(get_db)]

# Auto-error off so a missing header produces our own {detail, code} envelope (M6).
_bearer = HTTPBearer(auto_error=False)


# Adapters are process-wide singletons: Settings is not hashable, so these take no
# arguments and read the cached settings object themselves.
@lru_cache
def get_email_service() -> EmailService:
    """Console in P0; Resend is selected here in P1 when RESEND_API_KEY is set."""
    return ConsoleEmailService()


@lru_cache
def get_file_storage() -> FileStorage:
    """Local disk in P0; S3/MinIO is selected here in P1 when S3_ENDPOINT_URL is set."""
    return LocalDiskStorage(root=get_settings().upload_path)


@lru_cache
def get_attorney_directory() -> AttorneyDirectory:
    """Hash the seeded attorney password once per process, not per request (S4)."""
    settings = get_settings()
    return AttorneyDirectory(settings.attorney_email, settings.attorney_password)


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
