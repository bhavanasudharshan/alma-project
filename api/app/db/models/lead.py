"""The Lead aggregate: a prospective client who submitted the public form."""

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LeadState(StrEnum):
    """Intake pipeline state.

    Designed to grow (QUALIFIED, ENGAGED, DECLINED) without touching routers: the
    legal moves live in one transition table in ``services/lead_state.py`` (E1).
    """

    PENDING = "PENDING"
    REACHED_OUT = "REACHED_OUT"


def _utcnow() -> datetime:
    """Timezone-aware UTC now (stored naive-free so both SQLite and Postgres agree)."""
    return datetime.now(UTC)


class Lead(Base):
    """A prospect submission plus the attorney-managed intake state."""

    __tablename__ = "leads"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(320))

    # Storage key, never exposed to clients: the resume is served through
    # GET /leads/{id}/resume so the bytes stay behind auth (S1/C1).
    resume_key: Mapped[str] = mapped_column(String(512))
    resume_filename: Mapped[str] = mapped_column(String(255))
    resume_content_type: Mapped[str] = mapped_column(String(255))

    state: Mapped[LeadState] = mapped_column(String(32), default=LeadState.PENDING)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    # P1 (perf): the internal queue always filters on state and orders by created_at.
    __table_args__ = (
        Index("ix_leads_state", "state"),
        Index("ix_leads_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Lead {self.id} {self.state}>"
