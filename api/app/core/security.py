"""Password hashing and JWT issue/verify (S4/S1). No FastAPI imports."""

import logging
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from passlib.context import CryptContext

from app.core.config import Attorney, Settings
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


def create_access_token(sub: str, settings: Settings, name: str | None = None) -> str:
    """Issue a signed JWT for ``sub``, expiring per settings (8h default).

    ``name`` is carried for display only. Nothing is authorised on it -- the subject is
    still the email, and the roster is re-consulted on every request.
    """
    now = datetime.now(UTC)
    payload = {
        "sub": sub,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    if name:
        payload["name"] = name
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
    """The configured attorney roster (FR4/FR10).

    Every password is hashed once at construction, so no plaintext credential lives in
    memory beyond startup (S4). Authentication always costs exactly one bcrypt verify,
    whether or not the email is known, so response timing cannot be used to enumerate
    the roster -- see ``authenticate``.
    """

    def __init__(self, attorneys: Iterable[Attorney]) -> None:
        roster = list(attorneys)
        if not roster:
            raise ValueError("The attorney roster cannot be empty.")

        self._hashes: dict[str, str] = {}
        self._names: dict[str, str] = {}
        for attorney in roster:
            email = str(attorney.email).lower()
            self._hashes[email] = hash_password(attorney.password.get_secret_value())
            self._names[email] = attorney.name

        # Verified against when the email is unknown, so both paths do the same work.
        self._decoy_hash = next(iter(self._hashes.values()))

    def authenticate(self, email: str, password: str) -> str:
        """Return the attorney's email on success.

        :raises InvalidCredentials: on unknown email or wrong password -- deliberately
            the same error, after the same amount of work.
        """
        candidate = email.lower()
        stored = self._hashes.get(candidate, self._decoy_hash)
        password_matches = verify_password(password, stored)

        if candidate not in self._hashes or not password_matches:
            raise InvalidCredentials("Incorrect email or password.")
        return candidate

    def is_known(self, email: str) -> bool:
        """Whether ``email`` belongs to a configured attorney."""
        return email.lower() in self._hashes

    def name_for(self, email: str | None) -> str | None:
        """Display name for ``email``.

        ``None`` when the address is not (or is no longer) on the roster: an attorney
        can be removed from configuration while leads still record their assignment, and
        the historical fact stays true even though the name can no longer be resolved.
        """
        if not email:
            return None
        return self._names.get(email.lower())

    @property
    def emails(self) -> list[str]:
        """Every roster address, lower-cased."""
        return list(self._hashes)
