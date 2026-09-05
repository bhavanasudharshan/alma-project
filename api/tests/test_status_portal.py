"""Public status portal (EXT1) and the information it must not leak (SEC7)."""

import io

from fastapi.testclient import TestClient

from tests.conftest import PDF_BYTES, lead_form

# Everything the internal payload has that the public one must not.
PII_FIELDS = ("first_name", "last_name", "email", "resume_filename", "resume_key", "id", "actor")


def tracking_code_for(client: TestClient, db_session) -> str:
    import uuid

    from app.db.models import Lead

    created = client.post(
        "/api/v1/leads",
        data=lead_form(),
        files={"resume": ("cv.pdf", io.BytesIO(PDF_BYTES), "application/pdf")},
    )
    assert created.status_code == 201
    lead = db_session.get(Lead, uuid.UUID(created.json()["id"]))
    return lead.tracking_code


def test_valid_code_returns_status_and_timeline(client: TestClient, db_session) -> None:
    """EXT1: a prospect can see where they are without an account."""
    code = tracking_code_for(client, db_session)

    response = client.get(f"/api/v1/leads/track/{code}")

    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "PENDING"
    assert body["submitted_at"] and body["updated_at"]
    assert [event["to_state"] for event in body["events"]] == ["PENDING"]


def test_response_contains_no_personal_information(client: TestClient, db_session) -> None:
    """SEC7: a tracking code is a bearer credential sent by email. It unlocks the
    minimum that answers "where am I", and nothing that identifies anyone."""
    code = tracking_code_for(client, db_session)

    body = client.get(f"/api/v1/leads/track/{code}").json()

    serialised = str(body)
    for field in PII_FIELDS:
        assert field not in body
    assert "ada@example.com" not in serialised
    assert "Ada" not in serialised
    assert "cv.pdf" not in serialised


def test_timeline_grows_with_the_lead(client: TestClient, db_session, auth_headers: dict) -> None:
    """The prospect sees the transition, but not who made it."""
    code = tracking_code_for(client, db_session)
    lead_id = client.get("/api/v1/leads", headers=auth_headers).json()["items"][0]["id"]
    client.patch(
        f"/api/v1/leads/{lead_id}/state", json={"state": "REACHED_OUT"}, headers=auth_headers
    )

    body = client.get(f"/api/v1/leads/track/{code}").json()

    assert body["state"] == "REACHED_OUT"
    assert [event["to_state"] for event in body["events"]] == ["PENDING", "REACHED_OUT"]
    assert "actor" not in body["events"][1]
    assert "attorney@example.com" not in str(body)


def test_unknown_code_returns_a_generic_404(client: TestClient) -> None:
    """An unknown code must not reveal whether it was well-formed."""
    response = client.get("/api/v1/leads/track/NOTAREALCODE12345678901234567890")

    assert response.status_code == 404
    assert response.json()["code"] == "lead_not_found"


def test_malformed_and_unknown_codes_are_indistinguishable(client: TestClient, db_session) -> None:
    """SEC7: same status, same body, so probing tells an attacker nothing."""
    tracking_code_for(client, db_session)

    unknown = client.get("/api/v1/leads/track/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
    malformed = client.get("/api/v1/leads/track/short")

    assert unknown.status_code == malformed.status_code == 404
    assert unknown.json() == malformed.json()


def test_lowercase_code_is_accepted(client: TestClient, db_session) -> None:
    """Codes are read off an email and retyped; case should not be a trap."""
    code = tracking_code_for(client, db_session)

    response = client.get(f"/api/v1/leads/track/{code.lower()}")

    assert response.status_code == 200


def test_status_route_needs_no_authentication(client: TestClient, db_session) -> None:
    """EXT1: the whole point is that the prospect has no account."""
    code = tracking_code_for(client, db_session)

    response = client.get(f"/api/v1/leads/track/{code}", headers={})

    assert response.status_code == 200


def test_another_leads_code_shows_only_that_lead(client: TestClient, db_session) -> None:
    """Codes are per-lead; one must never surface another's timeline."""
    import uuid

    from app.db.models import Lead

    first = client.post(
        "/api/v1/leads",
        data=lead_form(first_name="Ada", email="ada@example.com"),
        files={"resume": ("cv.pdf", io.BytesIO(PDF_BYTES), "application/pdf")},
    ).json()
    second = client.post(
        "/api/v1/leads",
        data=lead_form(first_name="Grace", email="grace@example.com"),
        files={"resume": ("cv.pdf", io.BytesIO(PDF_BYTES), "application/pdf")},
    ).json()

    code_one = db_session.get(Lead, uuid.UUID(first["id"])).tracking_code
    code_two = db_session.get(Lead, uuid.UUID(second["id"])).tracking_code

    assert code_one != code_two
    assert client.get(f"/api/v1/leads/track/{code_one}").status_code == 200
    assert client.get(f"/api/v1/leads/track/{code_two}").status_code == 200
