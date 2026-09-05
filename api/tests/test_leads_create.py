"""Public lead submission: happy path and the upload allow-list (FR1, FR2, FR3, FR7, S2)."""

import io

from fastapi.testclient import TestClient

from tests.conftest import lead_form, resume_file
from tests.fakes import FakeEmailService, FakeStorage


def test_create_lead_returns_201_and_stores_the_resume(
    client: TestClient, storage: FakeStorage
) -> None:
    """FR1: a valid submission is accepted and the file reaches storage."""
    response = client.post("/api/v1/leads", data=lead_form(), files=resume_file())

    assert response.status_code == 201
    body = response.json()
    assert body["first_name"] == "Ada"
    assert body["email"] == "ada@example.com"
    assert body["resume_filename"] == "cv.pdf"
    assert len(storage.saved) == 1


def test_create_defaults_pending(client: TestClient) -> None:
    """FR7: a new lead starts in PENDING."""
    response = client.post("/api/v1/leads", data=lead_form(), files=resume_file())

    assert response.json()["state"] == "PENDING"


def test_response_never_exposes_the_storage_key(client: TestClient) -> None:
    """S1/C1: the storage layout is not part of the public contract."""
    response = client.post("/api/v1/leads", data=lead_form(), files=resume_file())

    assert "resume_key" not in response.json()


def test_emails_sent_to_prospect_and_attorney(client: TestClient, emails: FakeEmailService) -> None:
    """FR2/FR3: both notifications go out, to the lead and to the attorney inbox."""
    client.post(
        "/api/v1/leads",
        data=lead_form(email="grace@example.com"),
        files=resume_file(),
    )

    # FR10: the notification goes to the auto-assigned attorney, not a shared inbox.
    assert emails.recipients == ["grace@example.com", "attorney@example.com"]
    attorney_body = emails.sent[1]["text"]
    assert "Grace" not in attorney_body  # the form name was Ada, not the email local part
    assert "cv.pdf" in attorney_body


def test_timestamps_carry_an_explicit_utc_offset(client: TestClient) -> None:
    """E2: the wire format is identical on SQLite and Postgres."""
    response = client.post("/api/v1/leads", data=lead_form(), files=resume_file())

    body = response.json()
    # pydantic renders a UTC offset as the "Z" designator.
    assert body["created_at"].endswith("Z")
    assert body["updated_at"].endswith("Z")


def test_names_are_stripped(client: TestClient) -> None:
    """Whitespace around names is trimmed before persistence."""
    response = client.post(
        "/api/v1/leads",
        data=lead_form(first_name="  Ada  ", last_name="  Lovelace "),
        files=resume_file(),
    )

    body = response.json()
    assert body["first_name"] == "Ada"
    assert body["last_name"] == "Lovelace"


def test_email_is_lowercased(client: TestClient) -> None:
    """Addresses are normalised so lookups are case-insensitive."""
    response = client.post(
        "/api/v1/leads", data=lead_form(email="Ada@Example.COM"), files=resume_file()
    )

    assert response.json()["email"] == "ada@example.com"


def test_invalid_email_returns_422(client: TestClient) -> None:
    """FR1: a malformed address is rejected before anything is stored."""
    response = client.post(
        "/api/v1/leads", data=lead_form(email="not-an-email"), files=resume_file()
    )

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


def test_blank_first_name_returns_422(client: TestClient) -> None:
    """FR1: all four fields are required; whitespace is not a name."""
    response = client.post("/api/v1/leads", data=lead_form(first_name="   "), files=resume_file())

    assert response.status_code == 422


def test_wrong_content_type_returns_415(client: TestClient, storage: FakeStorage) -> None:
    """S2: the content-type allow-list rejects anything outside pdf/doc/docx."""
    response = client.post(
        "/api/v1/leads",
        data=lead_form(),
        files=resume_file(name="resume.exe", content_type="application/x-msdownload"),
    )

    assert response.status_code == 415
    assert response.json()["code"] == "unsupported_media_type"
    assert storage.saved == {}


def test_disallowed_extension_returns_415(client: TestClient) -> None:
    """S2: a permitted content-type with a mismatched extension is still refused."""
    response = client.post(
        "/api/v1/leads",
        data=lead_form(),
        files=resume_file(name="resume.exe", content_type="application/pdf"),
    )

    assert response.status_code == 415


def test_oversize_resume_returns_413(client: TestClient, storage: FakeStorage) -> None:
    """S2: uploads above max_resume_mb are refused and never stored."""
    oversize = b"x" * (5 * 1024 * 1024 + 1)
    response = client.post(
        "/api/v1/leads",
        data=lead_form(),
        files={"resume": ("big.pdf", io.BytesIO(oversize), "application/pdf")},
    )

    assert response.status_code == 413
    assert response.json()["code"] == "resume_too_large"
    assert storage.saved == {}


def test_empty_resume_is_rejected(client: TestClient) -> None:
    """An empty file is not a resume."""
    response = client.post("/api/v1/leads", data=lead_form(), files=resume_file(content=b""))

    assert response.status_code == 415


def test_missing_resume_returns_422(client: TestClient) -> None:
    """FR1: the resume is required."""
    response = client.post("/api/v1/leads", data=lead_form())

    assert response.status_code == 422
