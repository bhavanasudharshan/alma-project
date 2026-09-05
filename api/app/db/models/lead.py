"""The Lead aggregate: a prospective client who submitted the public form."""

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

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

    # EXT1: high-entropy public handle for the future status portal. Deliberately not
    # the primary key, so knowing one code reveals nothing about any other lead (SEC7).
    tracking_code: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    events: Mapped[list["LeadEvent"]] = relationship(
        back_populates="lead",
        cascade="all, delete-orphan",
        order_by="LeadEvent.created_at",
    )

    # P1 (perf): the internal queue always filters on state and orders by created_at.
    __table_args__ = (
        Index("ix_leads_state", "state"),
        Index("ix_leads_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Lead {self.id} {self.state}>"


class LeadEvent(Base):
    """Append-only audit row for every state change (SEC9-lite).

    Written in the same transaction as the state change itself, so the trail cannot
    disagree with the lead. Also the substrate for prospect notifications (EXT2) and
    the ops dashboard (EXT4).
    """

    __tablename__ = "lead_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("leads.id", ondelete="CASCADE"), index=True
    )
    # Null on the creation row: the lead came into existence rather than moving.
    from_state: Mapped[LeadState | None] = mapped_column(String(32), nullable=True)
    to_state: Mapped[LeadState] = mapped_column(String(32))
    # Attorney email for a manual change, or "system" for creation.
    actor: Mapped[str] = mapped_column(String(320))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    lead: Mapped["Lead"] = relationship(back_populates="events")

    def __repr__(self) -> str:
        return f"<LeadEvent {self.lead_id} {self.from_state}->{self.to_state}>"
