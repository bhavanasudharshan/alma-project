"""P1 public-surface hardening: uploads, honeypot, headers, audit trail."""

import io

import pytest
from fastapi.testclient import TestClient

from tests.conftest import DOCX_CONTENT_TYPE, PDF_BYTES, docx_bytes, lead_form

EXE_BYTES = b"MZ\x90\x00\x03\x00\x00\x00fake windows executable"


def upload(name: str, content: bytes, content_type: str) -> dict:
    return {"resume": (name, io.BytesIO(content), content_type)}


# --- SEC2: content must match the name -------------------------------------------


def test_exe_bytes_named_pdf_are_rejected(client: TestClient) -> None:
    """SEC2: the P0 audit showed renaming an .exe to .pdf got a 201. It must not."""
    response = client.post(
        "/api/v1/leads",
        data=lead_form(),
        files=upload("resume.pdf", EXE_BYTES, "application/pdf"),
    )

    assert response.status_code == 415
    assert response.json()["code"] == "unsupported_media_type"


def test_genuine_pdf_is_accepted(client: TestClient) -> None:
    """The sniffing must not reject real documents."""
    response = client.post(
        "/api/v1/leads", data=lead_form(), files=upload("cv.pdf", PDF_BYTES, "application/pdf")
    )

    assert response.status_code == 201


def test_genuine_docx_is_accepted(client: TestClient) -> None:
    """A .docx is a ZIP container; the sniffer sees the ZIP and must allow it."""
    response = client.post(
        "/api/v1/leads",
        data=lead_form(),
        files=upload("cv.docx", docx_bytes(), DOCX_CONTENT_TYPE),
    )

    assert response.status_code == 201


def test_legacy_doc_is_no_longer_accepted(client: TestClient) -> None:
    """SEC2(b): .doc is OLE and macro-prone, dropped in P1."""
    response = client.post(
        "/api/v1/leads",
        data=lead_form(),
        files=upload("cv.doc", PDF_BYTES, "application/msword"),
    )

    assert response.status_code == 415


def test_unrecognisable_bytes_are_rejected(client: TestClient) -> None:
    """A file with no recognisable signature is not a document."""
    response = client.post(
        "/api/v1/leads",
        data=lead_form(),
        files=upload("cv.pdf", b"just some plain text, not a pdf", "application/pdf"),
    )

    assert response.status_code == 415


def test_resume_download_sets_nosniff(
    client: TestClient, created_lead: dict, auth_headers: dict
) -> None:
    """SEC2(c): the browser must not re-interpret an uploaded file's type."""
    response = client.get(f"/api/v1/leads/{created_lead['id']}/resume", headers=auth_headers)

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Content-Disposition"].startswith("attachment")


# --- SEC4: honeypot ---------------------------------------------------------------


def test_honeypot_submission_is_silently_dropped(client: TestClient, emails) -> None:
    """SEC4: a filled hidden field means a bot. Answer 202, store nothing."""
    response = client.post(
        "/api/v1/leads",
        data={**lead_form(), "website": "http://spam.example"},
        files=upload("cv.pdf", PDF_BYTES, "application/pdf"),
    )

    assert response.status_code == 202
    assert emails.sent == []

    listed = client.get("/api/v1/leads", headers={"Authorization": "Bearer x"})
    assert listed.status_code == 401  # nothing to see, and nothing was created


def test_empty_honeypot_is_the_normal_path(client: TestClient) -> None:
    """A real browser leaves the field empty, which must behave exactly as before."""
    response = client.post(
        "/api/v1/leads",
        data={**lead_form(), "website": ""},
        files=upload("cv.pdf", PDF_BYTES, "application/pdf"),
    )

    assert response.status_code == 201


# --- SEC6: security headers -------------------------------------------------------


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        ("X-Content-Type-Options", "nosniff"),
        ("X-Frame-Options", "DENY"),
        ("Referrer-Policy", "no-referrer"),
        ("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'"),
    ],
)
def test_security_headers_are_present(client: TestClient, header: str, expected: str) -> None:
    """SEC6: baseline browser hardening on every API response."""
    response = client.get("/api/v1/health")

    assert response.headers[header] == expected


def test_hsts_is_absent_locally(client: TestClient) -> None:
    """HSTS pins to TLS, which local development does not have."""
    response = client.get("/api/v1/health")

    assert "Strict-Transport-Security" not in response.headers


# --- M5: request correlation ------------------------------------------------------


def test_request_id_is_generated_when_absent(client: TestClient) -> None:
    """M5: every response can be traced back to a log line."""
    response = client.get("/api/v1/health")

    assert response.headers["X-Request-ID"]


def test_inbound_request_id_is_echoed(client: TestClient) -> None:
    """A trace started upstream survives into this service's logs."""
    response = client.get("/api/v1/health", headers={"X-Request-ID": "trace-abc-123"})

    assert response.headers["X-Request-ID"] == "trace-abc-123"


# --- SEC9: audit trail ------------------------------------------------------------


def test_creation_writes_an_audit_event(
    client: TestClient, created_lead: dict, auth_headers: dict
) -> None:
    """SEC9: the trail starts at creation, with no from_state."""
    detail = client.get(f"/api/v1/leads/{created_lead['id']}", headers=auth_headers).json()

    assert len(detail["events"]) == 1
    assert detail["events"][0]["from_state"] is None
    assert detail["events"][0]["to_state"] == "PENDING"
    assert detail["events"][0]["actor"] == "system"


def test_state_change_appends_an_event_naming_the_attorney(
    client: TestClient, created_lead: dict, auth_headers: dict
) -> None:
    """SEC9: who changed what, when — the substrate for notifications and reporting."""
    client.patch(
        f"/api/v1/leads/{created_lead['id']}/state",
        json={"state": "REACHED_OUT"},
        headers=auth_headers,
    )

    detail = client.get(f"/api/v1/leads/{created_lead['id']}", headers=auth_headers).json()

    assert [e["to_state"] for e in detail["events"]] == ["PENDING", "REACHED_OUT"]
    assert detail["events"][1]["from_state"] == "PENDING"
    assert detail["events"][1]["actor"] == "attorney@example.com"


def test_rejected_transition_writes_no_event(
    client: TestClient, created_lead: dict, auth_headers: dict
) -> None:
    """The trail records what happened, not what was attempted."""
    client.patch(
        f"/api/v1/leads/{created_lead['id']}/state",
        json={"state": "PENDING"},
        headers=auth_headers,
    )

    detail = client.get(f"/api/v1/leads/{created_lead['id']}", headers=auth_headers).json()

    assert len(detail["events"]) == 1


def test_events_are_not_exposed_on_the_list_route(
    client: TestClient, created_lead: dict, auth_headers: dict
) -> None:
    """The trail is detail-only; the queue stays a lean payload."""
    page = client.get("/api/v1/leads", headers=auth_headers).json()

    assert "events" not in page["items"][0]


# --- EXT1: tracking code ----------------------------------------------------------


def test_every_lead_gets_a_high_entropy_tracking_code(
    client: TestClient, created_lead: dict, db_session
) -> None:
    """EXT1/SEC7: unguessable, and not derived from the lead id."""
    import uuid

    from app.db.models import Lead

    lead = db_session.get(Lead, uuid.UUID(created_lead["id"]))

    assert len(lead.tracking_code) == 32  # 160 bits, base32, unpadded
    assert lead.tracking_code.isalnum()
    assert lead.tracking_code not in created_lead["id"]


def test_tracking_code_is_not_exposed_on_the_internal_read(created_lead: dict) -> None:
    """It belongs to the prospect's email, not to the attorney payload (yet)."""
    assert "tracking_code" not in created_lead


def test_tracking_codes_are_unique_across_leads(client: TestClient, db_session) -> None:
    """A shared code would hand two prospects each other's status."""
    from app.db.models import Lead

    for name in ("Ada", "Grace", "Katherine"):
        client.post(
            "/api/v1/leads",
            data=lead_form(first_name=name, email=f"{name.lower()}@example.com"),
            files=upload("cv.pdf", PDF_BYTES, "application/pdf"),
        )

    codes = [lead.tracking_code for lead in db_session.query(Lead).all()]

    assert len(codes) == len(set(codes))
