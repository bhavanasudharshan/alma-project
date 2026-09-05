"""Attorney roster and lead assignment (FR10)."""

import io

from fastapi.testclient import TestClient

from tests.conftest import (
    ATTORNEY_EMAIL,
    ATTORNEY_NAME,
    ATTORNEY_PASSWORD,
    PDF_BYTES,
    SECOND_ATTORNEY_EMAIL,
    SECOND_ATTORNEY_NAME,
    SECOND_ATTORNEY_PASSWORD,
    THIRD_ATTORNEY_EMAIL,
    THIRD_ATTORNEY_PASSWORD,
    lead_form,
)


def headers_for(client: TestClient, email: str, password: str) -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def make_lead(client: TestClient, first_name: str = "Ada") -> str:
    response = client.post(
        "/api/v1/leads",
        data=lead_form(first_name=first_name, email=f"{first_name.lower()}@example.com"),
        files={"resume": ("cv.pdf", io.BytesIO(PDF_BYTES), "application/pdf")},
    )
    assert response.status_code == 201
    return response.json()["id"]


# --- roster login ------------------------------------------------------------------


def test_every_configured_attorney_can_sign_in(client: TestClient) -> None:
    """FR4/FR10: the roster is the set of accounts, not just the first one."""
    for email, password in [
        (ATTORNEY_EMAIL, ATTORNEY_PASSWORD),
        (SECOND_ATTORNEY_EMAIL, SECOND_ATTORNEY_PASSWORD),
        (THIRD_ATTORNEY_EMAIL, THIRD_ATTORNEY_PASSWORD),
    ]:
        response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert response.status_code == 200, email


def test_one_attorneys_password_does_not_work_for_another(client: TestClient) -> None:
    """Each account is verified against its own hash."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": SECOND_ATTORNEY_EMAIL, "password": ATTORNEY_PASSWORD},
    )

    assert response.status_code == 401


def test_unknown_email_is_still_indistinguishable(client: TestClient) -> None:
    """S4: an unknown address must not be cheaper or chattier than a wrong password."""
    unknown = client.post(
        "/api/v1/auth/login", json={"email": "nobody@example.com", "password": "wrong"}
    )
    wrong = client.post("/api/v1/auth/login", json={"email": ATTORNEY_EMAIL, "password": "wrong"})

    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json() == wrong.json()


def test_token_carries_the_display_name(client: TestClient) -> None:
    """The name is for display; nothing is authorised on it."""
    import jwt

    token = client.post(
        "/api/v1/auth/login", json={"email": ATTORNEY_EMAIL, "password": ATTORNEY_PASSWORD}
    ).json()["access_token"]

    claims = jwt.decode(token, options={"verify_signature": False})

    assert claims["sub"] == ATTORNEY_EMAIL
    assert claims["name"] == ATTORNEY_NAME


# --- assignment --------------------------------------------------------------------


def test_a_new_lead_is_auto_assigned(client: TestClient, auth_headers: dict) -> None:
    """FR10: with a roster configured, a submission never sits ownerless."""
    lead_id = make_lead(client)

    lead = client.get(f"/api/v1/leads/{lead_id}", headers=auth_headers).json()

    assert lead["assigned_to"] == ATTORNEY_EMAIL
    assert lead["assigned_to_name"] == ATTORNEY_NAME


def test_a_lead_can_be_returned_to_the_unassigned_pool(
    client: TestClient, auth_headers: dict
) -> None:
    """Clearing an assignment is still possible after auto-assignment."""
    lead_id = make_lead(client)

    response = client.patch(
        f"/api/v1/leads/{lead_id}/assign", json={"assignee": None}, headers=auth_headers
    )

    assert response.status_code == 200
    assert response.json()["assigned_to"] is None


def test_assign_to_self(client: TestClient, auth_headers: dict) -> None:
    """FR10: an attorney claims a lead and the name resolves from the roster."""
    lead_id = make_lead(client)

    response = client.patch(
        f"/api/v1/leads/{lead_id}/assign",
        json={"assignee": ATTORNEY_EMAIL},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["assigned_to"] == ATTORNEY_EMAIL
    assert response.json()["assigned_to_name"] == ATTORNEY_NAME


def test_reassign_to_another_attorney(client: TestClient, auth_headers: dict) -> None:
    """Reassignment is allowed through the API in this slice."""
    lead_id = make_lead(client)
    client.patch(
        f"/api/v1/leads/{lead_id}/assign", json={"assignee": ATTORNEY_EMAIL}, headers=auth_headers
    )

    response = client.patch(
        f"/api/v1/leads/{lead_id}/assign",
        json={"assignee": SECOND_ATTORNEY_EMAIL},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["assigned_to_name"] == SECOND_ATTORNEY_NAME


def test_unassign_with_null(client: TestClient, auth_headers: dict) -> None:
    """Clearing an assignment returns the lead to the unowned pool."""
    lead_id = make_lead(client)
    client.patch(
        f"/api/v1/leads/{lead_id}/assign", json={"assignee": ATTORNEY_EMAIL}, headers=auth_headers
    )

    response = client.patch(
        f"/api/v1/leads/{lead_id}/assign", json={"assignee": None}, headers=auth_headers
    )

    assert response.status_code == 200
    assert response.json()["assigned_to"] is None


def test_unknown_assignee_is_rejected(client: TestClient, auth_headers: dict) -> None:
    """FR10: only configured attorneys can own a lead."""
    lead_id = make_lead(client)

    response = client.patch(
        f"/api/v1/leads/{lead_id}/assign",
        json={"assignee": "stranger@example.com"},
        headers=auth_headers,
    )

    assert response.status_code == 422
    assert response.json()["code"] == "unknown_assignee"


def test_assigning_the_same_attorney_twice_is_idempotent(
    client: TestClient, auth_headers: dict
) -> None:
    """Unlike a state change, a repeated claim is not a conflict worth reporting.

    Two tabs, or a double click, mean the same thing: this lead should be mine. It
    already is, so answer 200 and leave the audit trail alone.
    """
    lead_id = make_lead(client)
    client.patch(
        f"/api/v1/leads/{lead_id}/assign", json={"assignee": ATTORNEY_EMAIL}, headers=auth_headers
    )

    second = client.patch(
        f"/api/v1/leads/{lead_id}/assign", json={"assignee": ATTORNEY_EMAIL}, headers=auth_headers
    )

    assert second.status_code == 200
    events = client.get(f"/api/v1/leads/{lead_id}", headers=auth_headers).json()["events"]
    assignment_events = [e for e in events if e["to_assignee"] or e["from_assignee"]]
    assert len(assignment_events) == 1


def test_assignment_writes_an_audit_row(client: TestClient, auth_headers: dict) -> None:
    """SEC9: who reassigned what to whom, and when."""
    lead_id = make_lead(client)

    client.patch(
        f"/api/v1/leads/{lead_id}/assign",
        json={"assignee": SECOND_ATTORNEY_EMAIL},
        headers=auth_headers,
    )

    events = client.get(f"/api/v1/leads/{lead_id}", headers=auth_headers).json()["events"]
    assignment = events[-1]
    # The lead was auto-assigned at creation, so this is a hand-off, not a first claim.
    assert assignment["from_assignee"] == ATTORNEY_EMAIL
    assert assignment["to_assignee"] == SECOND_ATTORNEY_EMAIL
    assert assignment["actor"] == ATTORNEY_EMAIL
    # The state did not move, so both ends record the state it stayed in.
    assert assignment["from_state"] == assignment["to_state"] == "PENDING"


def test_assignment_requires_authentication(client: TestClient) -> None:
    """S1: no anonymous path may change ownership."""
    lead_id = make_lead(client)

    response = client.patch(f"/api/v1/leads/{lead_id}/assign", json={"assignee": ATTORNEY_EMAIL})

    assert response.status_code == 401


def test_assigning_an_unknown_lead_returns_404(client: TestClient, auth_headers: dict) -> None:
    """A missing lead is a 404, distinct from a bad assignee."""
    response = client.patch(
        "/api/v1/leads/00000000-0000-0000-0000-000000000000/assign",
        json={"assignee": ATTORNEY_EMAIL},
        headers=auth_headers,
    )

    assert response.status_code == 404


# --- filtering ---------------------------------------------------------------------


def test_filter_by_assignee(client: TestClient, auth_headers: dict) -> None:
    """FR10: "Mine" is a server-side filter, like the state tabs."""
    mine = make_lead(client, "Ada")
    theirs = make_lead(client, "Grace")
    make_lead(client, "Katherine")

    client.patch(
        f"/api/v1/leads/{mine}/assign", json={"assignee": ATTORNEY_EMAIL}, headers=auth_headers
    )
    client.patch(
        f"/api/v1/leads/{theirs}/assign",
        json={"assignee": SECOND_ATTORNEY_EMAIL},
        headers=auth_headers,
    )

    page = client.get(f"/api/v1/leads?assigned_to={ATTORNEY_EMAIL}", headers=auth_headers).json()

    assert page["total"] == 1
    assert page["items"][0]["id"] == mine


def test_filter_unassigned(client: TestClient, auth_headers: dict) -> None:
    """The unowned pool is what an attorney picks work from."""
    make_lead(client, "Ada")
    released = make_lead(client, "Grace")
    # Everything is auto-assigned now, so create the unowned case explicitly.
    client.patch(f"/api/v1/leads/{released}/assign", json={"assignee": None}, headers=auth_headers)

    page = client.get("/api/v1/leads?assigned_to=unassigned", headers=auth_headers).json()

    assert page["total"] == 1
    assert page["items"][0]["assigned_to"] is None


def test_assignment_and_state_filters_combine(client: TestClient, auth_headers: dict) -> None:
    """The two filters intersect rather than override each other."""
    mine = make_lead(client, "Ada")
    client.patch(
        f"/api/v1/leads/{mine}/assign", json={"assignee": ATTORNEY_EMAIL}, headers=auth_headers
    )
    client.patch(f"/api/v1/leads/{mine}/state", json={"state": "REACHED_OUT"}, headers=auth_headers)
    other = make_lead(client, "Grace")
    client.patch(
        f"/api/v1/leads/{other}/assign", json={"assignee": ATTORNEY_EMAIL}, headers=auth_headers
    )

    page = client.get(
        f"/api/v1/leads?assigned_to={ATTORNEY_EMAIL}&state=REACHED_OUT", headers=auth_headers
    ).json()

    assert page["total"] == 1
    assert page["items"][0]["id"] == mine


# --- what the API must never expose -------------------------------------------------


def test_no_password_material_reaches_any_response(client: TestClient, auth_headers: dict) -> None:
    """S4: roster passwords and their hashes stay in the process, never on the wire."""
    lead_id = make_lead(client)
    client.patch(
        f"/api/v1/leads/{lead_id}/assign", json={"assignee": ATTORNEY_EMAIL}, headers=auth_headers
    )

    bodies = [
        client.get("/api/v1/leads", headers=auth_headers).text,
        client.get(f"/api/v1/leads/{lead_id}", headers=auth_headers).text,
        client.post(
            "/api/v1/auth/login", json={"email": ATTORNEY_EMAIL, "password": ATTORNEY_PASSWORD}
        ).text,
    ]

    for body in bodies:
        assert ATTORNEY_PASSWORD not in body
        assert "$2b$" not in body  # a bcrypt hash prefix
        assert "password" not in body.lower()


def test_the_display_name_is_present_where_expected(client: TestClient, auth_headers: dict) -> None:
    """FR10: the queue shows a human name, not an email, once assigned."""
    lead_id = make_lead(client)
    client.patch(
        f"/api/v1/leads/{lead_id}/assign", json={"assignee": ATTORNEY_EMAIL}, headers=auth_headers
    )

    page = client.get("/api/v1/leads", headers=auth_headers).json()

    assert page["items"][0]["assigned_to_name"] == ATTORNEY_NAME
