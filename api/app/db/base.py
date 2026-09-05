"""Declarative base for all ORM models (M3: Alembic autogenerate targets this metadata)."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class every SQLAlchemy model inherits from."""
