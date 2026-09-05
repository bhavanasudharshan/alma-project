"""Authentication request/response models."""

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    """Attorney credentials (FR4)."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Bearer token issued on successful login."""

    access_token: str
    # Not a credential: the literal OAuth2 scheme name.
    token_type: str = "bearer"  # noqa: S105
