"""Password hashing and JWT issue/verify (S4/S1). No FastAPI imports."""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from passlib.context import CryptContext

from app.core.config import Settings
from app.services.exceptions import InvalidCredentials

logger = logging.getLogger(__name__)

# bcrypt with passlib's constant-time verify. Cost is the library default (12 rounds).
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Return a bcrypt hash. The plaintext is never stored anywhere (S4)."""
    return _pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Constant-time comparison of ``plain`` against a bcrypt hash (S4)."""
    return _pwd_context.verify(plain, hashed)


def create_access_token(sub: str, settings: Settings) -> str:
    """Issue a signed JWT for ``sub``, expiring per settings (8h default)."""
    now = datetime.now(UTC)
    payload = {
        "sub": sub,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str, settings: Settings) -> dict[str, Any]:
    """Verify signature and expiry, returning the claims.

    :raises InvalidCredentials: for any malformed, expired or badly signed token. The
        reason is logged but never returned to the caller (S1).
    """
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        logger.info("Rejected token: %s", exc)
        raise InvalidCredentials("Could not validate credentials.") from exc


class AttorneyDirectory:
    """The single seeded attorney account (FR4).

    The password is hashed once at startup so no plaintext credential lives in memory
    beyond construction, and a wrong email still costs a bcrypt verify so the endpoint
    does not leak which half was wrong (S4).
    """

    def __init__(self, email: str, password: str) -> None:
        self._email = email.lower()
        self._password_hash = hash_password(password)

    def authenticate(self, email: str, password: str) -> str:
        """Return the attorney's email on success.

        :raises InvalidCredentials: on unknown email or wrong password.
        """
        matches_email = email.lower() == self._email
        matches_password = verify_password(password, self._password_hash)
        if not (matches_email and matches_password):
            raise InvalidCredentials("Incorrect email or password.")
        return self._email

    def is_known(self, email: str) -> bool:
        """Whether ``email`` is the seeded attorney."""
        return email.lower() == self._email
