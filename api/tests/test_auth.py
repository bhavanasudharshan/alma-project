"""Attorney login and bearer-token enforcement (FR4, S1, S4)."""

from fastapi.testclient import TestClient

from tests.conftest import ATTORNEY_EMAIL, ATTORNEY_PASSWORD

INTERNAL_ROUTES = [
    ("get", "/api/v1/leads"),
    ("get", "/api/v1/leads/00000000-0000-0000-0000-000000000000"),
    ("get", "/api/v1/leads/00000000-0000-0000-0000-000000000000/resume"),
    ("patch", "/api/v1/leads/00000000-0000-0000-0000-000000000000/state"),
]


def test_login_returns_a_bearer_token(client: TestClient) -> None:
    """FR4: correct credentials yield a usable token."""
    response = client.post(
        "/api/v1/auth/login", json={"email": ATTORNEY_EMAIL, "password": ATTORNEY_PASSWORD}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_is_case_insensitive_on_email(client: TestClient) -> None:
    """The seeded address matches regardless of case."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": ATTORNEY_EMAIL.upper(), "password": ATTORNEY_PASSWORD},
    )

    assert response.status_code == 200


def test_wrong_password_returns_401(client: TestClient) -> None:
    """S4: a wrong password is refused."""
    response = client.post(
        "/api/v1/auth/login", json={"email": ATTORNEY_EMAIL, "password": "wrong"}
    )

    assert response.status_code == 401
    assert response.json()["code"] == "invalid_credentials"


def test_unknown_email_and_wrong_password_are_indistinguishable(client: TestClient) -> None:
    """S4: the error must not reveal which half of the credential was wrong."""
    unknown = client.post(
        "/api/v1/auth/login", json={"email": "nobody@example.com", "password": "wrong"}
    )
    wrong_password = client.post(
        "/api/v1/auth/login", json={"email": ATTORNEY_EMAIL, "password": "wrong"}
    )

    assert unknown.status_code == wrong_password.status_code == 401
    assert unknown.json() == wrong_password.json()


def test_internal_routes_require_a_token(client: TestClient) -> None:
    """S1: no anonymous path reaches lead data."""
    for method, path in INTERNAL_ROUTES:
        response = getattr(client, method)(path)
        assert response.status_code == 401, f"{method.upper()} {path} was reachable"
        assert response.json()["code"] == "not_authenticated"


def test_internal_routes_reject_a_bad_token(client: TestClient) -> None:
    """S1: a forged or corrupt token is refused."""
    headers = {"Authorization": "Bearer not-a-real-token"}
    for method, path in INTERNAL_ROUTES:
        response = getattr(client, method)(path, headers=headers)
        assert response.status_code == 401, f"{method.upper()} {path} accepted a bad token"


def test_token_signed_with_another_secret_is_rejected(client: TestClient) -> None:
    """S1: the signature, not merely the shape of the token, is what is trusted."""
    import jwt

    forged = jwt.encode({"sub": ATTORNEY_EMAIL}, "attacker-secret", algorithm="HS256")

    response = client.get("/api/v1/leads", headers={"Authorization": f"Bearer {forged}"})

    assert response.status_code == 401


def test_public_submission_needs_no_token(client: TestClient) -> None:
    """FR1: the prospect form stays public."""
    from tests.conftest import lead_form, resume_file

    response = client.post("/api/v1/leads", data=lead_form(), files=resume_file())

    assert response.status_code == 201
