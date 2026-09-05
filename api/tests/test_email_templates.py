"""Email rendering: every field present, and prospect input escaped (FR2/FR3, SEC3)."""

from app.services.email.messages import (
    LeadSnapshot,
    attorney_notification,
    prospect_confirmation,
)

NOTIFY = "intake@example.com"
UI_URL = "http://localhost:3000/leads"


def snapshot(**overrides) -> LeadSnapshot:
    base = {
        "id": "0b5f0c1e-0000-0000-0000-000000000000",
        "first_name": "Ada",
        "last_name": "Lovelace",
        "email": "ada@example.com",
        "resume_filename": "cv.pdf",
        "resume_content_type": "application/pdf",
        "state": "PENDING",
        "tracking_code": "ABCD1234EFGH5678",
        "received_at": "2026-01-01 12:00:00 UTC",
    }
    return LeadSnapshot(**{**base, **overrides})


def test_prospect_confirmation_contains_every_field() -> None:
    """FR2: the confirmation echoes what we received, plus the tracking code (EXT1)."""
    message = prospect_confirmation(snapshot())

    assert message.to == "ada@example.com"
    for expected in ("Ada", "Lovelace", "ada@example.com", "cv.pdf", "ABCD1234EFGH5678"):
        assert expected in message.text
        assert expected in message.html


def test_attorney_notification_contains_every_field() -> None:
    """FR3: the attorney gets the full lead detail and a link to the queue."""
    message = attorney_notification(snapshot(), notify_email=NOTIFY, internal_ui_url=UI_URL)

    assert message.to == NOTIFY
    for expected in ("Ada", "Lovelace", "ada@example.com", "cv.pdf", "PENDING", UI_URL):
        assert expected in message.text
        assert expected in message.html


def test_both_messages_have_a_text_fallback() -> None:
    """A text part is always present for clients that will not render HTML."""
    for message in (
        prospect_confirmation(snapshot()),
        attorney_notification(snapshot(), NOTIFY, UI_URL),
    ):
        assert message.text.strip()
        assert message.html is not None


def test_script_in_a_name_is_escaped_in_the_attorney_html(caplog) -> None:
    """SEC3: prospect-supplied text is data, never markup, in the attorney's inbox."""
    message = attorney_notification(
        snapshot(first_name="<script>alert(1)</script>"), NOTIFY, UI_URL
    )

    assert "<script>alert(1)</script>" not in message.html
    assert "&lt;script&gt;" in message.html
    # The plain-text part is not markup, so it legitimately carries the raw characters.
    assert "<script>" in message.text


def test_html_attributes_cannot_be_broken_out_of() -> None:
    """SEC3: quotes in prospect input are escaped, not passed through."""
    message = prospect_confirmation(snapshot(first_name='" onmouseover="evil()'))

    assert 'onmouseover="evil()"' not in message.html
    assert "&#34;" in message.html or "&quot;" in message.html


def test_subject_strips_crlf_so_headers_cannot_be_injected() -> None:
    """SEC3: a subject is a header; newlines in one are header injection."""
    message = attorney_notification(
        snapshot(first_name="Ada\r\nBcc: attacker@example.com"), NOTIFY, UI_URL
    )

    assert "\r" not in message.subject
    assert "\n" not in message.subject
    assert "Bcc:" in message.subject  # flattened to one line, not silently dropped


def test_snapshot_is_detached_from_the_orm(created_lead: dict, db_session) -> None:
    """The background task must not depend on an open session.

    LeadSnapshot is a frozen dataclass of plain strings, so rendering after the request
    finishes cannot trigger a lazy load against a closed session.
    """
    from app.db.models import Lead

    lead = db_session.get(Lead, __import__("uuid").UUID(created_lead["id"]))
    snap = LeadSnapshot.from_lead(lead)

    db_session.close()

    message = prospect_confirmation(snap)  # must not raise DetachedInstanceError
    assert snap.tracking_code in message.text
