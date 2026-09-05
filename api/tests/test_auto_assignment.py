"""Auto-assignment on submit, and the emails that follow it (FR10)."""

import io

from fastapi.testclient import TestClient

from tests.conftest import (
    ATTORNEY_EMAIL,
    PDF_BYTES,
    SECOND_ATTORNEY_EMAIL,
    THIRD_ATTORNEY_EMAIL,
    lead_form,
)
from tests.fakes import FakeEmailService

ROSTER_ORDER = [ATTORNEY_EMAIL, SECOND_ATTORNEY_EMAIL, THIRD_ATTORNEY_EMAIL]


def submit(client: TestClient, name: str) -> dict:
    response = client.post(
        "/api/v1/leads",
        data=lead_form(first_name=name, email=f"{name.lower()}@example.com"),
        files={"resume": ("cv.pdf", io.BytesIO(PDF_BYTES), "application/pdf")},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_first_submission_goes_to_the_first_roster_attorney(client: TestClient) -> None:
    """Ties break on roster order, so a cold start is deterministic."""
    lead = submit(client, "Ada")

    assert lead["assigned_to"] == ATTORNEY_EMAIL


def test_submissions_spread_across_the_roster(client: TestClient) -> None:
    """FR10: each new lead goes to whoever currently has the fewest open ones."""
    assignees = [submit(client, name)["assigned_to"] for name in ("Ada", "Grace", "Kath")]

    assert assignees == ROSTER_ORDER


def test_the_round_repeats_once_everyone_has_one(client: TestClient) -> None:
    """Four leads across three attorneys: the fourth returns to the front."""
    names = ("Ada", "Grace", "Kath", "Dot")

    assignees = [submit(client, name)["assigned_to"] for name in names]

    assert assignees == [*ROSTER_ORDER, ATTORNEY_EMAIL]


def test_qualified_leads_stop_counting_as_load(client: TestClient, auth_headers: dict) -> None:
    """A closed-out lead should not keep counting against the attorney who handled it."""
    first = submit(client, "Ada")  # -> attorney 1
    submit(client, "Grace")  # -> attorney 2
    submit(client, "Kath")  # -> attorney 3

    url = f"/api/v1/leads/{first['id']}/state"
    client.patch(url, json={"state": "REACHED_OUT"}, headers=auth_headers)
    client.patch(url, json={"state": "QUALIFIED"}, headers=auth_headers)

    # Attorney 1 now has zero *open* leads, so they are the least loaded again.
    assert submit(client, "Dot")["assigned_to"] == ATTORNEY_EMAIL


def test_assignment_is_written_in_the_same_transaction(
    client: TestClient, auth_headers: dict
) -> None:
    """SEC9/FR10: the creation event records the owner, so a lead is never ownerless."""
    lead = submit(client, "Ada")

    events = client.get(f"/api/v1/leads/{lead['id']}", headers=auth_headers).json()["events"]

    assert len(events) == 1
    assert events[0]["actor"] == "system"
    assert events[0]["from_assignee"] is None
    assert events[0]["to_assignee"] == ATTORNEY_EMAIL


def test_prospect_confirmation_ccs_the_assignee_only(
    client: TestClient, emails: FakeEmailService
) -> None:
    """N: the owning attorney is copied; a shared inbox never is (C1)."""
    submit(client, "Ada")

    confirmation = next(m for m in emails.sent if m["subject"] == "We received your information")
    assert confirmation["to"] == "ada@example.com"
    assert confirmation["cc"] == [ATTORNEY_EMAIL]
    assert confirmation["reply_to"] == ATTORNEY_EMAIL
    # intake@example.com is the shared inbox in the test settings.
    assert "intake@example.com" not in (confirmation["cc"] or [])


def test_attorney_notification_goes_to_the_assignee_not_the_shared_inbox(
    client: TestClient, emails: FakeEmailService
) -> None:
    """The person who owns the lead is the person told about it."""
    submit(client, "Ada")

    notification = next(m for m in emails.sent if m["subject"].startswith("New lead"))
    assert notification["to"] == ATTORNEY_EMAIL


def test_status_update_names_the_attorney_and_sets_reply_to(
    client: TestClient, auth_headers: dict, emails: FakeEmailService
) -> None:
    """M(b): a status change reads as a message from a person, not a system."""
    lead = submit(client, "Ada")
    emails.sent.clear()

    client.patch(
        f"/api/v1/leads/{lead['id']}/state", json={"state": "REACHED_OUT"}, headers=auth_headers
    )

    update = emails.sent[0]
    assert "Test Attorney has reached out" in update["text"]
    assert update["reply_to"] == ATTORNEY_EMAIL


def test_confirmation_mentions_review_and_reach_out(
    client: TestClient, emails: FakeEmailService
) -> None:
    """M(a): the applicant is told what happens next."""
    submit(client, "Ada")

    confirmation = next(m for m in emails.sent if m["subject"] == "We received your information")
    assert "review your application and reach out" in confirmation["text"]


# --- empty roster: the single-account fallback ------------------------------------


def test_empty_roster_leaves_leads_unassigned_and_uses_the_shared_inbox(tmp_path) -> None:
    """N: with no ATTORNEYS configured, nothing is auto-assigned and mail goes to the
    shared inbox — the zero-config reviewer run is unchanged ($1)."""
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.core.deps import (
        get_attorney_directory,
        get_email_service,
        get_file_storage,
        get_settings,
    )
    from app.core.security import AttorneyDirectory
    from app.db.base import Base
    from app.db.models import Lead  # noqa: F401
    from app.db.session import get_db
    from app.main import create_app
    from tests.conftest import (
        ATTORNEY_PASSWORD,
        build_settings,
        database_url_for_tests,
        engine_kwargs,
    )
    from tests.fakes import FakeStorage

    settings = build_settings(
        database_url=database_url_for_tests(tmp_path),
        upload_dir=str(tmp_path / "uploads"),
        jwt_secret_key="test-secret-key-of-sufficient-length",
        attorney_email=ATTORNEY_EMAIL,
        attorney_password=ATTORNEY_PASSWORD,
        attorney_notify_email="intake@example.com",
        attorneys=[],  # the whole point of this test
    )
    engine = create_engine(settings.database_url, **engine_kwargs(settings.database_url))
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()
    mailbox = FakeEmailService()

    app = create_app(settings)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_db] = lambda: session
    app.dependency_overrides[get_file_storage] = FakeStorage
    app.dependency_overrides[get_email_service] = lambda: mailbox
    app.dependency_overrides[get_attorney_directory] = lambda: AttorneyDirectory(settings.roster)

    try:
        with TestClient(app) as client:
            lead = submit(client, "Ada")

        assert lead["assigned_to"] is None

        confirmation = next(
            m for m in mailbox.sent if m["subject"] == "We received your information"
        )
        assert confirmation["cc"] is None
        assert confirmation["reply_to"] is None

        notification = next(m for m in mailbox.sent if m["subject"].startswith("New lead"))
        assert notification["to"] == "intake@example.com"
    finally:
        session.close()
        engine.dispose()
