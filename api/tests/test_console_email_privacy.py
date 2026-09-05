"""The console adapter must not write lead PII into INFO logs (C1)."""

import logging

from app.services.email.console import ConsoleEmailService

BODY = "Hi Ada,\nYour resume cv.pdf was received. Email: ada@example.com"


def test_info_carries_only_recipient_subject_and_lead_id(caplog) -> None:
    """Logs are long-lived and widely readable; the body repeats the prospect's details."""
    caplog.set_level(logging.INFO, logger="app.services.email.console")

    ConsoleEmailService().send(
        to="ada@example.com", subject="We received your information", text=BODY, lead_id="lead-1"
    )

    info = [r for r in caplog.records if r.levelno == logging.INFO]
    assert len(info) == 1
    rendered = info[0].getMessage()
    assert "ada@example.com" in rendered  # the recipient is the point of the line
    assert "lead-1" in rendered
    assert "Your resume cv.pdf was received" not in rendered  # the body is not


def test_body_is_available_at_debug(caplog) -> None:
    """Reviewers running the demo still need to read the message they just triggered."""
    caplog.set_level(logging.DEBUG, logger="app.services.email.console")

    ConsoleEmailService().send(
        to="ada@example.com", subject="We received your information", text=BODY, lead_id="lead-1"
    )

    debug = [r for r in caplog.records if r.levelno == logging.DEBUG]
    assert any("Your resume cv.pdf was received" in r.getMessage() for r in debug)


def test_send_never_raises() -> None:
    """R1: a broken notifier must not surface into the request path."""
    ConsoleEmailService().send(to="x@example.com", subject="s", text="t")
