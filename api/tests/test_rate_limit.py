"""Per-IP rate limiting on the public surface (SEC1).

The autouse fixture in conftest disables limits for the rest of the suite; these tests
turn them back on, and reset the limiter's counters so runs stay independent.
"""

import io

import pytest
from fastapi.testclient import TestClient

from app.core.limiter import limiter
from tests.conftest import ATTORNEY_EMAIL, PDF_BYTES, lead_form


@pytest.fixture
def limited() -> None:
    """Enable the limiter and start from a clean slate."""
    limiter.enabled = True
    limiter.reset()
    yield
    limiter.reset()
    limiter.enabled = False


def submit(client: TestClient) -> int:
    return client.post(
        "/api/v1/leads",
        data=lead_form(),
        files={"resume": ("cv.pdf", io.BytesIO(PDF_BYTES), "application/pdf")},
    ).status_code


def test_sixth_submission_is_rate_limited(client: TestClient, limited: None) -> None:
    """SEC1: the configured 5/10min budget is enforced, and the 6th call is refused."""
    codes = [submit(client) for _ in range(6)]

    assert codes[:5] == [201] * 5
    assert codes[5] == 429


def test_rate_limited_response_uses_the_standard_envelope(
    client: TestClient, limited: None
) -> None:
    """M6: even the limiter's rejection carries {detail, code}, plus Retry-After."""
    for _ in range(5):
        submit(client)

    response = client.post(
        "/api/v1/leads",
        data=lead_form(),
        files={"resume": ("cv.pdf", io.BytesIO(PDF_BYTES), "application/pdf")},
    )

    assert response.status_code == 429
    assert response.json()["code"] == "rate_limited"
    # 5/10minutes -> a 600 second window.
    assert response.headers["Retry-After"] == "600"


def test_login_has_its_own_budget(client: TestClient, limited: None) -> None:
    """SEC1: login is limited separately so guessing cannot be parallelised cheaply."""
    codes = [
        client.post(
            "/api/v1/auth/login", json={"email": ATTORNEY_EMAIL, "password": "wrong"}
        ).status_code
        for _ in range(11)
    ]

    assert codes[:10] == [401] * 10
    assert codes[10] == 429


def test_limits_do_not_apply_to_internal_reads(
    client: TestClient, auth_headers: dict, limited: None
) -> None:
    """An attorney refreshing the queue must not lock themselves out."""
    codes = [client.get("/api/v1/leads", headers=auth_headers).status_code for _ in range(15)]

    assert set(codes) == {200}
