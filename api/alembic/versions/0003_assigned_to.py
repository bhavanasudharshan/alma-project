"""Add lead assignment (FR10).

All three columns are nullable, so no backfill is needed: existing leads are simply
unassigned, which is the correct answer for data that predates the feature.

Revision ID: 0003_assigned_to
Revises: 0002_events_tracking
Create Date: 2026-09-05 12:56:11.810890

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003_assigned_to"
down_revision: str | None = "0002_events_tracking"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add leads.assigned_to and the assignment columns on lead_events."""
    with op.batch_alter_table("lead_events", schema=None) as batch_op:
        batch_op.add_column(sa.Column("from_assignee", sa.String(length=320), nullable=True))
        batch_op.add_column(sa.Column("to_assignee", sa.String(length=320), nullable=True))

    with op.batch_alter_table("leads", schema=None) as batch_op:
        batch_op.add_column(sa.Column("assigned_to", sa.String(length=320), nullable=True))
        batch_op.create_index(batch_op.f("ix_leads_assigned_to"), ["assigned_to"], unique=False)


def downgrade() -> None:
    """Drop the assignment columns."""
    with op.batch_alter_table("leads", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_leads_assigned_to"))
        batch_op.drop_column("assigned_to")

    with op.batch_alter_table("lead_events", schema=None) as batch_op:
        batch_op.drop_column("to_assignee")
        batch_op.drop_column("from_assignee")
