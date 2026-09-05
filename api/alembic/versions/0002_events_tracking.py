"""Add the lead audit trail and public tracking code (SEC9-lite, EXT1).

``tracking_code`` is added in three steps rather than one: adding a NOT NULL column to
a table that already holds rows fails, and by this point a reviewer may already have
submitted leads under 0001. Add nullable, backfill each existing row with its own
high-entropy code, then tighten the constraint (M3).
"""

import secrets
from base64 import b32encode
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_events_tracking"
down_revision: str | None = "0001_leads"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Must match app.services.lead_service._TRACKING_CODE_BYTES.
_TRACKING_CODE_BYTES = 20


def _new_code() -> str:
    return b32encode(secrets.token_bytes(_TRACKING_CODE_BYTES)).decode().rstrip("=")


def upgrade() -> None:
    """Create ``lead_events`` and add ``leads.tracking_code``."""
    op.create_table(
        "lead_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("lead_id", sa.Uuid(), nullable=False),
        sa.Column("from_state", sa.String(length=32), nullable=True),
        sa.Column("to_state", sa.String(length=32), nullable=False),
        sa.Column("actor", sa.String(length=320), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("lead_events", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_lead_events_lead_id"), ["lead_id"], unique=False)

    # Step 1: nullable, so existing rows are legal.
    with op.batch_alter_table("leads", schema=None) as batch_op:
        batch_op.add_column(sa.Column("tracking_code", sa.String(length=64), nullable=True))

    # Step 2: backfill. Each row gets its own code -- a shared placeholder would break
    # the unique index and hand several prospects the same public handle (SEC7).
    connection = op.get_bind()
    leads = sa.table("leads", sa.column("id", sa.Uuid()), sa.column("tracking_code", sa.String()))
    for (lead_id,) in connection.execute(sa.select(leads.c.id)).fetchall():
        connection.execute(
            leads.update().where(leads.c.id == lead_id).values(tracking_code=_new_code())
        )

    # Step 3: tighten to NOT NULL + UNIQUE now that every row has a value.
    with op.batch_alter_table("leads", schema=None) as batch_op:
        batch_op.alter_column("tracking_code", existing_type=sa.String(length=64), nullable=False)
        batch_op.create_index(batch_op.f("ix_leads_tracking_code"), ["tracking_code"], unique=True)


def downgrade() -> None:
    """Drop the tracking code and the audit trail."""
    with op.batch_alter_table("leads", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_leads_tracking_code"))
        batch_op.drop_column("tracking_code")

    with op.batch_alter_table("lead_events", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_lead_events_lead_id"))

    op.drop_table("lead_events")
