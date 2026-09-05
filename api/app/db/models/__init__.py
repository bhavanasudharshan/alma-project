"""ORM models. Imported here so Alembic autogenerate sees every table (M3)."""

from app.db.models.lead import Lead, LeadEvent, LeadState

__all__ = ["Lead", "LeadEvent", "LeadState"]
