"""Test fixtures: an isolated app over a temp SQLite file with fake adapters (M2)."""

import io
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.core.deps import (
    get_attorney_directory,
    get_email_service,
    get_file_storage,
    get_settings,
)
from app.core.security import AttorneyDirectory
from app.db.base import Base
from app.db.models import Lead  # noqa: F401  (registers the table on Base.metadata)
from app.db.session import get_db
from app.main import create_app
from tests.fakes import FakeEmailService, FakeStorage

ATTORNEY_EMAIL = "attorney@example.com"
ATTORNEY_PASSWORD = "test-password"

PDF_BYTES = b"%PDF-1.4 fake resume bytes"
PDF_CONTENT_TYPE = "application/pdf"


@pytest.fixture
def settings(tmp_path) -> Settings:
    """Settings pointing at a throwaway database and upload directory."""
    return Settings(
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        upload_dir=str(tmp_path / "uploads"),
        jwt_secret_key="test-secret-key-of-sufficient-length",
        attorney_email=ATTORNEY_EMAIL,
        attorney_password=ATTORNEY_PASSWORD,
        attorney_notify_email="intake@example.com",
        max_resume_mb=5,
    )


@pytest.fixture
def db_session(settings: Settings) -> Iterator[Session]:
    """A session on a fresh schema, created from the models rather than migrations."""
    engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def storage() -> FakeStorage:
    """In-memory file storage."""
    return FakeStorage()


@pytest.fixture
def emails() -> FakeEmailService:
    """In-memory email sink."""
    return FakeEmailService()


@pytest.fixture
def client(
    settings: Settings,
    db_session: Session,
    storage: FakeStorage,
    emails: FakeEmailService,
) -> Iterator[TestClient]:
    """A TestClient whose adapters are all fakes and whose DB is per-test."""
    app = create_app(settings)

    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_file_storage] = lambda: storage
    app.dependency_overrides[get_email_service] = lambda: emails
    app.dependency_overrides[get_attorney_directory] = lambda: AttorneyDirectory(
        ATTORNEY_EMAIL, ATTORNEY_PASSWORD
    )

    # raise_server_exceptions=False so the 500 handler is exercised like in production.
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def token(client: TestClient) -> str:
    """A valid attorney bearer token."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": ATTORNEY_EMAIL, "password": ATTORNEY_PASSWORD},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


@pytest.fixture
def auth_headers(token: str) -> dict[str, str]:
    """Authorization header for internal routes."""
    return {"Authorization": f"Bearer {token}"}


def resume_file(
    name: str = "cv.pdf",
    content: bytes = PDF_BYTES,
    content_type: str = PDF_CONTENT_TYPE,
) -> dict:
    """Build the multipart ``files=`` argument for a resume upload."""
    return {"resume": (name, io.BytesIO(content), content_type)}


def lead_form(
    first_name: str = "Ada",
    last_name: str = "Lovelace",
    email: str = "ada@example.com",
) -> dict[str, str]:
    """Build the multipart ``data=`` argument for the public form."""
    return {"first_name": first_name, "last_name": last_name, "email": email}


@pytest.fixture
def created_lead(client: TestClient) -> dict:
    """A lead already submitted through the public endpoint."""
    response = client.post("/api/v1/leads", data=lead_form(), files=resume_file())
    assert response.status_code == 201, response.text
    return response.json()
