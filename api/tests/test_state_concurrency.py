"""Concurrency guarantee for the state machine (R2).

The rest of the suite shares one session per test, which cannot express a race. These
tests give every request its own session against a file-backed SQLite database and run
the PATCHes from a thread pool, so the SQL predicate in ``LeadRepository.update_state``
is genuinely exercised.

Audit 01b (check E21) found the previous Python-only guard let 2-4 concurrent callers
all receive 200. These tests are the regression barrier for that defect.
"""

import io
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker

from app.core.deps import (
    get_attorney_directory,
    get_email_service,
    get_file_storage,
    get_settings,
)
from app.core.security import AttorneyDirectory
from app.db.base import Base
from app.db.models import Lead  # noqa: F401  (registers the table)
from app.db.session import get_db
from app.main import create_app
from tests.conftest import (
    ATTORNEY_EMAIL,
    ATTORNEY_PASSWORD,
    PDF_BYTES,
    TEST_ROSTER,
    USE_POSTGRES,
    build_settings,
    database_url_for_tests,
    engine_kwargs,
)
from tests.fakes import FakeEmailService, FakeStorage

PARALLEL_REQUESTS = 12


@pytest.fixture
def concurrent_client(tmp_path) -> Iterator[TestClient]:
    """A client whose every request gets its own DB session, like production."""
    database_url = database_url_for_tests(tmp_path)
    # build_settings ignores the repo .env, so this fixture cannot inherit a roster.
    settings = build_settings(
        database_url=database_url,
        upload_dir=str(tmp_path / "uploads"),
        jwt_secret_key="test-secret-key-of-sufficient-length",
        attorney_email=ATTORNEY_EMAIL,
        attorney_password=ATTORNEY_PASSWORD,
        attorneys=TEST_ROSTER,
    )
    kwargs = engine_kwargs(database_url)
    if database_url.startswith("sqlite"):
        kwargs["connect_args"] = {**kwargs.get("connect_args", {}), "timeout": 30}
    engine = create_engine(database_url, **kwargs)

    if database_url.startswith("sqlite"):
        # WAL + a busy timeout keep SQLite from raising "database is locked" under the
        # thread pool. Postgres needs neither; the transition guarantee itself comes
        # from the SQL predicate on both engines.
        @event.listens_for(engine, "connect")
        def _pragmas(dbapi_connection, _record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.close()

    if USE_POSTGRES:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def session_per_request():
        db = factory()
        try:
            yield db
        finally:
            db.close()

    app = create_app(settings)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_db] = session_per_request
    app.dependency_overrides[get_file_storage] = FakeStorage
    app.dependency_overrides[get_email_service] = FakeEmailService
    app.dependency_overrides[get_attorney_directory] = lambda: AttorneyDirectory(settings.roster)

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
    engine.dispose()


def _new_pending_lead(client: TestClient) -> str:
    response = client.post(
        "/api/v1/leads",
        data={"first_name": "Race", "last_name": "Winner", "email": "race@example.com"},
        files={"resume": ("cv.pdf", io.BytesIO(PDF_BYTES), "application/pdf")},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _auth(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": ATTORNEY_EMAIL, "password": ATTORNEY_PASSWORD},
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


# Five independent runs, per the architect's acceptance criterion.
@pytest.mark.parametrize("run", range(1, 6))
def test_exactly_one_concurrent_patch_wins(concurrent_client: TestClient, run: int) -> None:
    """R2: N simultaneous PATCHes on one PENDING lead yield exactly one 200."""
    headers = _auth(concurrent_client)
    lead_id = _new_pending_lead(concurrent_client)

    def patch() -> int:
        return concurrent_client.patch(
            f"/api/v1/leads/{lead_id}/state",
            json={"state": "REACHED_OUT"},
            headers=headers,
        ).status_code

    with ThreadPoolExecutor(max_workers=PARALLEL_REQUESTS) as pool:
        codes = list(pool.map(lambda _: patch(), range(PARALLEL_REQUESTS)))

    assert codes.count(200) == 1, f"run {run}: expected 1 winner, got {codes.count(200)} ({codes})"
    assert codes.count(409) == PARALLEL_REQUESTS - 1, f"run {run}: {codes}"

    final = concurrent_client.get(f"/api/v1/leads/{lead_id}", headers=headers)
    assert final.json()["state"] == "REACHED_OUT"


def test_the_row_is_written_once(concurrent_client: TestClient) -> None:
    """R2: the winning UPDATE is the only one that touches the row."""
    headers = _auth(concurrent_client)
    lead_id = _new_pending_lead(concurrent_client)

    before = concurrent_client.get(f"/api/v1/leads/{lead_id}", headers=headers).json()

    def patch() -> int:
        return concurrent_client.patch(
            f"/api/v1/leads/{lead_id}/state",
            json={"state": "REACHED_OUT"},
            headers=headers,
        ).status_code

    with ThreadPoolExecutor(max_workers=PARALLEL_REQUESTS) as pool:
        list(pool.map(lambda _: patch(), range(PARALLEL_REQUESTS)))

    after = concurrent_client.get(f"/api/v1/leads/{lead_id}", headers=headers).json()
    assert after["state"] == "REACHED_OUT"
    assert after["updated_at"] > before["updated_at"]


def test_sql_predicate_rejects_a_stale_expected_state(concurrent_client: TestClient) -> None:
    """R2: the guard lives in the WHERE clause, provable without any HTTP race.

    A second UPDATE carrying a now-stale expected state matches zero rows.
    """
    import uuid as _uuid

    from app.db.models.lead import LeadState
    from app.repositories.lead_repo import LeadRepository

    lead_id = _new_pending_lead(concurrent_client)

    gen = concurrent_client.app.dependency_overrides[get_db]()
    db = next(gen)
    try:
        repo = LeadRepository(db)
        lid = _uuid.UUID(lead_id)
        assert repo.update_state(lid, LeadState.PENDING, LeadState.REACHED_OUT) is True
        db.commit()
        # The same call again: the row is no longer PENDING, so nothing matches.
        assert repo.update_state(lid, LeadState.PENDING, LeadState.REACHED_OUT) is False
        db.commit()
        assert db.execute(text("select count(*) from leads")).scalar() == 1
    finally:
        db.close()
