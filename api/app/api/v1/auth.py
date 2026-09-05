"""Authentication routes (FR4). Transport only -- verification lives in core/security."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.deps import SettingsDep, get_attorney_directory
from app.core.security import AttorneyDirectory, create_access_token
from app.schemas.auth import LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Exchange attorney credentials for a bearer token",
    responses={401: {"description": "Incorrect email or password"}},
)
def login(
    payload: LoginRequest,
    settings: SettingsDep,
    directory: Annotated[AttorneyDirectory, Depends(get_attorney_directory)],
) -> TokenResponse:
    """Return a JWT for the seeded attorney.

    Bad credentials raise ``InvalidCredentials``, which the global handler renders as
    a 401 with the same message for unknown email and wrong password alike (S4).
    """
    subject = directory.authenticate(payload.email, payload.password)
    return TokenResponse(access_token=create_access_token(subject, settings))
