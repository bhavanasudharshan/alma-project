"""Listing, filtering and pagination of the attorney queue (FR5)."""

from fastapi.testclient import TestClient

from tests.conftest import lead_form, resume_file


def _submit(client: TestClient, first_name: str) -> str:
    response = client.post(
        "/api/v1/leads",
        data=lead_form(first_name=first_name, email=f"{first_name.lower()}@example.com"),
        files=resume_file(),
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_list_returns_all_leads_with_a_total(client: TestClient, auth_headers: dict) -> None:
    """FR5: the queue shows every lead plus the count for pagination."""
    for name in ("Ada", "Grace", "Katherine"):
        _submit(client, name)

    response = client.get("/api/v1/leads", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert len(body["items"]) == 3
    assert body["limit"] == 50
    assert body["offset"] == 0


def test_list_filters_by_state(client: TestClient, auth_headers: dict) -> None:
    """FR5: the PENDING / REACHED_OUT tabs are a server-side filter."""
    first = _submit(client, "Ada")
    _submit(client, "Grace")
    client.patch(
        f"/api/v1/leads/{first}/state", json={"state": "REACHED_OUT"}, headers=auth_headers
    )

    pending = client.get("/api/v1/leads?state=PENDING", headers=auth_headers).json()
    reached = client.get("/api/v1/leads?state=REACHED_OUT", headers=auth_headers).json()

    assert pending["total"] == 1
    assert pending["items"][0]["first_name"] == "Grace"
    assert reached["total"] == 1
    assert reached["items"][0]["id"] == first


def test_list_paginates(client: TestClient, auth_headers: dict) -> None:
    """FR5: limit and offset walk the queue, and total stays the full count."""
    for name in ("Ada", "Grace", "Katherine"):
        _submit(client, name)

    page = client.get("/api/v1/leads?limit=2&offset=0", headers=auth_headers).json()
    tail = client.get("/api/v1/leads?limit=2&offset=2", headers=auth_headers).json()

    assert page["total"] == tail["total"] == 3
    assert len(page["items"]) == 2
    assert len(tail["items"]) == 1
    ids = {item["id"] for item in page["items"]} | {item["id"] for item in tail["items"]}
    assert len(ids) == 3


def test_list_rejects_an_out_of_range_limit(client: TestClient, auth_headers: dict) -> None:
    """A caller cannot ask for an unbounded page."""
    response = client.get("/api/v1/leads?limit=5000", headers=auth_headers)

    assert response.status_code == 422


def test_get_single_lead(client: TestClient, created_lead: dict, auth_headers: dict) -> None:
    """A lead is fetchable by id."""
    response = client.get(f"/api/v1/leads/{created_lead['id']}", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["id"] == created_lead["id"]


def test_get_unknown_lead_returns_404(client: TestClient, auth_headers: dict) -> None:
    """A missing id is a clean 404 in the standard envelope."""
    response = client.get(
        "/api/v1/leads/00000000-0000-0000-0000-000000000000", headers=auth_headers
    )

    assert response.status_code == 404
    assert response.json() == {"detail": response.json()["detail"], "code": "lead_not_found"}
