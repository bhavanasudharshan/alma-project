"""Lead request/response models. The API contract lives here, not in the ORM (E3)."""

import uuid
from datetime import UTC, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.db.models.lead import LeadState

NameStr = Annotated[str, Field(min_length=1, max_length=100)]


class LeadCreate(BaseModel):
    """Validated public form submission (FR1)."""

    first_name: NameStr
    last_name: NameStr
    email: EmailStr

    @field_validator("first_name", "last_name", mode="before")
    @classmethod
    def _strip(cls, value: str) -> str:
        """Trim surrounding whitespace before the length check runs."""
        return value.strip() if isinstance(value, str) else value

    @field_validator("email", mode="after")
    @classmethod
    def _lowercase(cls, value: str) -> str:
        """Store addresses lowercased so lookups and dedupe are case-insensitive."""
        return value.lower()


class LeadRead(BaseModel):
    """Lead as returned to the attorney UI.

    ``resume_key`` is deliberately absent: the storage layout is not a public
    contract and the bytes are only reachable through the authenticated
    ``/leads/{id}/resume`` route (S1/C1).
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    first_name: str
    last_name: str
    email: EmailStr
    resume_filename: str
    resume_content_type: str
    state: LeadState
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at", mode="after")
    @classmethod
    def _as_utc(cls, value: datetime) -> datetime:
        """Always serialise an explicit UTC offset.

        Timestamps are written as timezone-aware UTC, but SQLite has no offset type
        and hands them back naive. Postgres does not. Re-attaching UTC here keeps the
        wire format identical on both engines so the web client never guesses (E2).
        """
        return value if value.tzinfo else value.replace(tzinfo=UTC)


class LeadListResponse(BaseModel):
    """One page of leads plus the total matching count (FR5)."""

    items: list[LeadRead]
    total: int
    limit: int
    offset: int


class LeadStateUpdate(BaseModel):
    """Requested state change (FR8)."""

    state: LeadState
