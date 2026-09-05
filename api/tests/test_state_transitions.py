"""Lead state machine over HTTP and in isolation (FR8, FR9, E1, R2)."""

import pytest
from fastapi.testclient import TestClient

from app.db.models.lead import LeadState
from app.services.exceptions import AlreadyInState, InvalidTransition
from app.services.lead_state import assert_transition


def test_pending_to_reached_out_returns_200(
    client: TestClient, created_lead: dict, auth_headers: dict
) -> None:
    """FR8: the attorney marks a pending lead as reached out."""
    response = client.patch(
        f"/api/v1/leads/{created_lead['id']}/state",
        json={"state": "REACHED_OUT"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["state"] == "REACHED_OUT"


def test_reached_out_to_reached_out_returns_409(
    client: TestClient, created_lead: dict, auth_headers: dict
) -> None:
    """FR9/R2: repeating the transition is a conflict, not a silent success.

    P1 splits the vocabulary: this is `already_in_state` (benign, the UI refreshes and
    says so calmly) rather than `invalid_transition` (a move the pipeline forbids).
    """
    url = f"/api/v1/leads/{created_lead['id']}/state"
    client.patch(url, json={"state": "REACHED_OUT"}, headers=auth_headers)

    response = client.patch(url, json={"state": "REACHED_OUT"}, headers=auth_headers)

    assert response.status_code == 409
    assert response.json()["code"] == "already_in_state"


def test_pending_to_pending_returns_409(
    client: TestClient, created_lead: dict, auth_headers: dict
) -> None:
    """FR9: re-asserting the current state is not a legal move."""
    response = client.patch(
        f"/api/v1/leads/{created_lead['id']}/state",
        json={"state": "PENDING"},
        headers=auth_headers,
    )

    assert response.status_code == 409
    assert response.json()["code"] == "already_in_state"


def test_unknown_state_returns_422(
    client: TestClient, created_lead: dict, auth_headers: dict
) -> None:
    """A state outside the enum never reaches the transition table."""
    response = client.patch(
        f"/api/v1/leads/{created_lead['id']}/state",
        json={"state": "ARCHIVED"},
        headers=auth_headers,
    )

    assert response.status_code == 422


def test_patch_unknown_lead_returns_404(client: TestClient, auth_headers: dict) -> None:
    """A missing lead is a 404, distinct from an illegal transition."""
    response = client.patch(
        "/api/v1/leads/00000000-0000-0000-0000-000000000000/state",
        json={"state": "REACHED_OUT"},
        headers=auth_headers,
    )

    assert response.status_code == 404
    assert response.json()["code"] == "lead_not_found"


def test_reached_out_to_qualified_returns_200(
    client: TestClient, created_lead: dict, auth_headers: dict
) -> None:
    """E1: the new state works end to end after a 3-line backend change."""
    url = f"/api/v1/leads/{created_lead['id']}/state"
    client.patch(url, json={"state": "REACHED_OUT"}, headers=auth_headers)

    response = client.patch(url, json={"state": "QUALIFIED"}, headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["state"] == "QUALIFIED"


def test_pending_to_qualified_returns_409(
    client: TestClient, created_lead: dict, auth_headers: dict
) -> None:
    """E1/FR9: the pipeline has an order; QUALIFIED cannot be reached directly."""
    response = client.patch(
        f"/api/v1/leads/{created_lead['id']}/state",
        json={"state": "QUALIFIED"},
        headers=auth_headers,
    )

    assert response.status_code == 409
    assert response.json()["code"] == "invalid_transition"


def test_qualified_is_terminal(client: TestClient, created_lead: dict, auth_headers: dict) -> None:
    """Nothing follows QUALIFIED yet, so every move out of it is refused."""
    url = f"/api/v1/leads/{created_lead['id']}/state"
    client.patch(url, json={"state": "REACHED_OUT"}, headers=auth_headers)
    client.patch(url, json={"state": "QUALIFIED"}, headers=auth_headers)

    for target in ("PENDING", "REACHED_OUT"):
        response = client.patch(url, json={"state": target}, headers=auth_headers)
        assert response.status_code == 409, target


def test_qualified_appears_in_the_audit_trail(
    client: TestClient, created_lead: dict, auth_headers: dict
) -> None:
    """SEC9: the new state is recorded like any other."""
    url = f"/api/v1/leads/{created_lead['id']}/state"
    client.patch(url, json={"state": "REACHED_OUT"}, headers=auth_headers)
    client.patch(url, json={"state": "QUALIFIED"}, headers=auth_headers)

    detail = client.get(f"/api/v1/leads/{created_lead['id']}", headers=auth_headers).json()

    assert [e["to_state"] for e in detail["events"]] == ["PENDING", "REACHED_OUT", "QUALIFIED"]


def test_list_filters_by_the_new_state(
    client: TestClient, created_lead: dict, auth_headers: dict
) -> None:
    """FR5: the new filter tab is a server-side filter like the others."""
    url = f"/api/v1/leads/{created_lead['id']}/state"
    client.patch(url, json={"state": "REACHED_OUT"}, headers=auth_headers)
    client.patch(url, json={"state": "QUALIFIED"}, headers=auth_headers)

    qualified = client.get("/api/v1/leads?state=QUALIFIED", headers=auth_headers).json()

    assert qualified["total"] == 1
    assert qualified["items"][0]["state"] == "QUALIFIED"


def test_transition_rules_carry_notification_intent() -> None:
    """EXT2: each edge declares whether the prospect should hear about it."""
    from app.services.lead_state import rule_for

    rule = rule_for(LeadState.PENDING, LeadState.REACHED_OUT)

    assert rule is not None
    assert rule.notify_prospect is True

    onward = rule_for(LeadState.REACHED_OUT, LeadState.QUALIFIED)
    assert onward is not None and onward.notify_prospect is True

    assert rule_for(LeadState.REACHED_OUT, LeadState.PENDING) is None


def test_transition_table_is_the_only_authority() -> None:
    """E1: the rules are assertable without HTTP, a DB, or any adapter."""
    assert_transition(LeadState.PENDING, LeadState.REACHED_OUT)

    # A move the pipeline forbids.
    with pytest.raises(InvalidTransition):
        assert_transition(LeadState.REACHED_OUT, LeadState.PENDING)
    # Asking for the state it is already in: distinct, benign, still a 409.
    with pytest.raises(AlreadyInState):
        assert_transition(LeadState.PENDING, LeadState.PENDING)
