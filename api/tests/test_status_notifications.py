"""Prospect notifications on state change (EXT2)."""

from fastapi.testclient import TestClient

from tests.fakes import FakeEmailService


def patch_state(client: TestClient, lead_id: str, state: str, headers: dict):
    return client.patch(f"/api/v1/leads/{lead_id}/state", json={"state": state}, headers=headers)


def test_reached_out_emails_the_prospect(
    client: TestClient, created_lead: dict, auth_headers: dict, emails: FakeEmailService
) -> None:
    """EXT2: the transition rule says notify_prospect, so the prospect hears about it."""
    emails.sent.clear()

    patch_state(client, created_lead["id"], "REACHED_OUT", auth_headers)

    assert emails.recipients == ["ada@example.com"]
    assert emails.sent[0]["subject"] == "An update on your submission"
    assert "reaching out" in emails.sent[0]["text"]


def test_qualified_emails_the_prospect_with_its_own_copy(
    client: TestClient, created_lead: dict, auth_headers: dict, emails: FakeEmailService
) -> None:
    """Each state carries its own wording, not one generic message."""
    patch_state(client, created_lead["id"], "REACHED_OUT", auth_headers)
    emails.sent.clear()

    patch_state(client, created_lead["id"], "QUALIFIED", auth_headers)

    assert len(emails.sent) == 1
    assert "strong fit" in emails.sent[0]["text"]


def test_the_status_email_carries_the_portal_link_and_code(
    client: TestClient, created_lead: dict, auth_headers: dict, emails: FakeEmailService
) -> None:
    """EXT1 + EXT2: the update tells them where to look for more."""
    emails.sent.clear()

    patch_state(client, created_lead["id"], "REACHED_OUT", auth_headers)

    body = emails.sent[0]["text"]
    assert "/status" in body
    assert "tracking code" in body.lower()


def test_a_rejected_transition_sends_nothing(
    client: TestClient, created_lead: dict, auth_headers: dict, emails: FakeEmailService
) -> None:
    """No state change means no notification."""
    emails.sent.clear()

    response = patch_state(client, created_lead["id"], "QUALIFIED", auth_headers)

    assert response.status_code == 409
    assert emails.sent == []


def test_a_repeated_transition_does_not_re_notify(
    client: TestClient, created_lead: dict, auth_headers: dict, emails: FakeEmailService
) -> None:
    """R2 + EXT2: only the caller who actually moved the row triggers the email.

    This is what makes the SQL-predicate guard matter beyond correctness -- without it,
    several concurrent callers would each send the prospect the same update.
    """
    patch_state(client, created_lead["id"], "REACHED_OUT", auth_headers)
    emails.sent.clear()

    second = patch_state(client, created_lead["id"], "REACHED_OUT", auth_headers)

    assert second.status_code == 409
    assert emails.sent == []


def test_the_email_is_sent_after_the_state_is_committed(
    client: TestClient, created_lead: dict, auth_headers: dict, emails: FakeEmailService
) -> None:
    """R1: the change is durable before anyone is told about it."""
    emails.sent.clear()

    patch_state(client, created_lead["id"], "REACHED_OUT", auth_headers)

    # The background task ran, and the state it announced is the state that persisted.
    assert emails.sent
    current = client.get(f"/api/v1/leads/{created_lead['id']}", headers=auth_headers).json()
    assert current["state"] == "REACHED_OUT"


def test_a_provider_failure_does_not_fail_the_request(
    client: TestClient, created_lead: dict, auth_headers: dict
) -> None:
    """R1: a broken notifier must never undo an accepted state change."""
    from app.core.deps import get_email_service

    class ExplodingEmailService:
        def send(self, **kwargs):
            raise RuntimeError("provider down")

    client.app.dependency_overrides[get_email_service] = ExplodingEmailService

    response = patch_state(client, created_lead["id"], "REACHED_OUT", auth_headers)

    assert response.status_code == 200
    assert response.json()["state"] == "REACHED_OUT"


def test_every_notifying_state_has_prospect_copy() -> None:
    """EXT2: a state flagged notify_prospect must have words to send.

    Silence used to be the safe default -- a state with no copy simply sent nothing.
    That is quiet in the wrong way: someone adds a state, flags it for notification,
    and no one finds out the prospect was never told. Fail loudly here instead.
    """
    from app.services.email.messages import _STATUS_COPY
    from app.services.lead_state import TRANSITIONS

    missing = sorted(
        {
            to_state
            for edges in TRANSITIONS.values()
            for to_state, rule in edges.items()
            if rule.notify_prospect and to_state not in _STATUS_COPY
        }
    )

    assert not missing, (
        f"These states are flagged notify_prospect but have no entry in _STATUS_COPY, "
        f"so the prospect would never hear about them: {missing}"
    )
