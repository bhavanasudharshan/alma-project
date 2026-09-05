"""Engine and session factory (M1: the only module that knows how to reach the DB)."""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import REPO_ROOT, get_settings

_SQLITE_RELATIVE_PREFIX = "sqlite:///./"


def resolve_database_url(database_url: str) -> str:
    """Anchor a relative SQLite URL to the repo root and ensure its directory exists.

    ``sqlite:///./data/alma.db`` is otherwise resolved against the current working
    directory, so ``make api`` (cwd ``api/``) and ``pytest`` (cwd repo root) would open
    two different files. Non-SQLite URLs are returned untouched (E2).
    """
    if not database_url.startswith(_SQLITE_RELATIVE_PREFIX):
        return database_url
    db_path = REPO_ROOT / database_url[len(_SQLITE_RELATIVE_PREFIX) :]
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{db_path}"


def _engine_kwargs(database_url: str) -> dict:
    """SQLite needs a per-connection flag that Postgres must not receive (E2)."""
    if database_url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    return {}


_database_url = resolve_database_url(get_settings().database_url)

engine = create_engine(_database_url, **_engine_kwargs(_database_url))
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a request-scoped session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
