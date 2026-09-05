"""Data access for leads. The only layer that writes SQL (CLAUDE.md layering)."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.db.models.lead import Lead, LeadEvent, LeadState


class LeadRepository:
    """Persistence operations on the ``leads`` table."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def create(self, lead: Lead) -> Lead:
        """Insert ``lead`` and flush so its server-side defaults are populated."""
        self._db.add(lead)
        self._db.flush()
        return lead

    def add_event(
        self,
        lead_id: uuid.UUID,
        from_state: LeadState | None,
        to_state: LeadState,
        actor: str,
        from_assignee: str | None = None,
        to_assignee: str | None = None,
    ) -> LeadEvent:
        """Append an audit row (SEC9).

        Flushed but not committed: the caller commits it in the same transaction as the
        change it describes, so the trail and the lead can never disagree.
        """
        event = LeadEvent(
            lead_id=lead_id,
            from_state=from_state,
            to_state=to_state,
            actor=actor,
            from_assignee=from_assignee,
            to_assignee=to_assignee,
        )
        self._db.add(event)
        self._db.flush()
        return event

    def list_events(self, lead_id: uuid.UUID) -> list[LeadEvent]:
        """Return a lead's audit trail, oldest first."""
        return list(
            self._db.scalars(
                select(LeadEvent)
                .where(LeadEvent.lead_id == lead_id)
                .order_by(LeadEvent.created_at, LeadEvent.id)
            )
        )

    def get_by_tracking_code(self, tracking_code: str) -> Lead | None:
        """Look a lead up by its public tracking code (EXT1)."""
        return self._db.scalar(select(Lead).where(Lead.tracking_code == tracking_code))

    def get(self, lead_id: uuid.UUID) -> Lead | None:
        """Return the lead with ``lead_id``, or ``None``."""
        return self._db.get(Lead, lead_id)

    def list(
        self,
        state: LeadState | None = None,
        assigned_to: str | None = None,
        unassigned_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Lead], int]:
        """Return one page of leads, newest first, plus the total matching count (FR5).

        The count runs against the same filter so the caller can paginate correctly.
        """
        filters = []
        if state is not None:
            filters.append(Lead.state == state)
        if unassigned_only:
            filters.append(Lead.assigned_to.is_(None))
        elif assigned_to is not None:
            filters.append(Lead.assigned_to == assigned_to)

        total = self._db.scalar(select(func.count()).select_from(Lead).where(*filters)) or 0
        items = list(
            self._db.scalars(
                select(Lead)
                .where(*filters)
                .order_by(Lead.created_at.desc(), Lead.id.desc())
                .limit(limit)
                .offset(offset)
            )
        )
        return items, total

    def update_assignee(self, lead_id: uuid.UUID, current: str | None, new: str | None) -> bool:
        """Atomically move a lead from ``current`` to ``new`` assignee (FR10).

        Same predicate-in-the-WHERE-clause approach as ``update_state``: the database,
        not a prior SELECT, decides who wins when two attorneys claim the same lead at
        the same moment.

        :returns: ``True`` if this call performed the change.
        """
        condition = Lead.assigned_to.is_(None) if current is None else Lead.assigned_to == current
        result = self._db.execute(
            update(Lead)
            .where(Lead.id == lead_id, condition)
            .values(assigned_to=new, updated_at=datetime.now(UTC))
            .execution_options(synchronize_session=False)
        )
        return bool(result.rowcount)

    def update_state(
        self, lead_id: uuid.UUID, current_state: LeadState, new_state: LeadState
    ) -> bool:
        """Atomically move a lead from ``current_state`` to ``new_state`` (R2).

        The expected state is part of the WHERE clause, so the database -- not a
        prior SELECT in Python -- decides who wins a race. Two concurrent requests
        cannot both succeed: the second matches zero rows.

        :returns: ``True`` if this call performed the transition, ``False`` if the
            row was no longer in ``current_state`` (someone else got there first).
        """
        result = self._db.execute(
            update(Lead)
            .where(Lead.id == lead_id, Lead.state == current_state)
            .values(state=new_state, updated_at=datetime.now(UTC))
            .execution_options(synchronize_session=False)
        )
        return bool(result.rowcount)
