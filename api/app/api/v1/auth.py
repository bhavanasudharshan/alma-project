"""Authentication routes (FR4). Transport only -- verification lives in core/security."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.core.deps import SettingsDep, get_attorney_directory
from app.core.limiter import limiter, login_limit
from app.core.security import AttorneyDirectory, create_access_token
from app.schemas.auth import LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Exchange attorney credentials for a bearer token",
    responses={
        401: {"description": "Incorrect email or password"},
        429: {"description": "Too many login attempts from this address"},
    },
)
@limiter.limit(login_limit)
def login(
    request: Request,
    payload: LoginRequest,
    settings: SettingsDep,
    directory: Annotated[AttorneyDirectory, Depends(get_attorney_directory)],
) -> TokenResponse:
    """Return a JWT for the seeded attorney.

    Bad credentials raise ``InvalidCredentials``, which the global handler renders as
    a 401 with the same message for unknown email and wrong password alike (S4).
    Per-IP rate limited so the endpoint cannot be used for online guessing (SEC1).
    """
    subject = directory.authenticate(payload.email, payload.password)
    return TokenResponse(
        access_token=create_access_token(subject, settings, name=directory.name_for(subject))
    )
