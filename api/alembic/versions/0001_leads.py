"""Create the leads table (FR1, M3).

Indexes on state and created_at back the attorney queue's filter + newest-first sort.

Revision ID: 0001_leads
Revises:
Create Date: 2026-09-05 10:01:41.757478

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001_leads"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create ``leads`` with its two query indexes."""
    op.create_table(
        "leads",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("resume_key", sa.String(length=512), nullable=False),
        sa.Column("resume_filename", sa.String(length=255), nullable=False),
        sa.Column("resume_content_type", sa.String(length=255), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("leads", schema=None) as batch_op:
        batch_op.create_index("ix_leads_created_at", ["created_at"], unique=False)
        batch_op.create_index("ix_leads_state", ["state"], unique=False)


def downgrade() -> None:
    """Drop ``leads`` and its indexes."""
    with op.batch_alter_table("leads", schema=None) as batch_op:
        batch_op.drop_index("ix_leads_state")
        batch_op.drop_index("ix_leads_created_at")

    op.drop_table("leads")
