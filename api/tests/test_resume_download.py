"""Resume download and the storage adapter's safety properties (FR6, S2, A1)."""

import io

import pytest
from fastapi.testclient import TestClient

from app.services.storage.local import (
    LocalDiskStorage,
    build_key,
    display_filename,
    sanitise_filename,
)
from tests.conftest import PDF_BYTES, lead_form, resume_file
from tests.fakes import FailingStorage


def test_download_streams_the_original_file(
    client: TestClient, created_lead: dict, auth_headers: dict
) -> None:
    """FR6: the attorney gets the stored bytes back under the original filename."""
    response = client.get(f"/api/v1/leads/{created_lead['id']}/resume", headers=auth_headers)

    assert response.status_code == 200
    assert response.content == PDF_BYTES
    assert response.headers["content-type"].startswith("application/pdf")
    assert "cv.pdf" in response.headers["content-disposition"]


def test_download_filename_cannot_carry_a_path(client: TestClient, auth_headers: dict) -> None:
    """S2: a traversal filename must not reach the client in Content-Disposition.

    quote() defaults to safe="/", so an unsanitised name would emit
    ``filename*=UTF-8\'\'../../etc/passwd.pdf`` and let a careless download client
    write outside its download directory.
    """
    created = client.post(
        "/api/v1/leads",
        data=lead_form(),
        files={"resume": ("../../etc/passwd.pdf", io.BytesIO(PDF_BYTES), "application/pdf")},
    )
    assert created.status_code == 201

    response = client.get(f"/api/v1/leads/{created.json()['id']}/resume", headers=auth_headers)

    disposition = response.headers["content-disposition"]
    assert "../" not in disposition
    assert "/" not in disposition.split("filename*=UTF-8''")[1]
    assert disposition.endswith("passwd.pdf")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("../../etc/passwd.pdf", "passwd.pdf"),
        ("..\\..\\win\\sys32.pdf", "sys32.pdf"),
        (".bashrc", "bashrc"),
        ("", "resume"),
        # Unicode is preserved: the storage key is ASCII, the display name is not.
        ("résumé señor.pdf", "résumé señor.pdf"),
    ],
)
def test_display_filename_flattens_without_mangling_unicode(raw: str, expected: str) -> None:
    """S2/C1: no path component survives, but accented names reach the attorney intact."""
    assert display_filename(raw) == expected


def test_unicode_filename_survives_the_download_header(
    client: TestClient, auth_headers: dict
) -> None:
    """C1: an accented resume name is percent-encoded, not replaced with underscores."""
    created = client.post(
        "/api/v1/leads",
        data=lead_form(),
        files={"resume": ("résumé.pdf", io.BytesIO(PDF_BYTES), "application/pdf")},
    )

    response = client.get(f"/api/v1/leads/{created.json()['id']}/resume", headers=auth_headers)

    # RFC 5987 percent-encoding of "résumé.pdf"
    assert "r%C3%A9sum%C3%A9.pdf" in response.headers["content-disposition"]


def test_download_requires_auth(client: TestClient, created_lead: dict) -> None:
    """S1: resume bytes are never reachable anonymously."""
    response = client.get(f"/api/v1/leads/{created_lead['id']}/resume")

    assert response.status_code == 401


def test_download_unknown_lead_returns_404(client: TestClient, auth_headers: dict) -> None:
    """A missing lead has no resume."""
    response = client.get(
        "/api/v1/leads/00000000-0000-0000-0000-000000000000/resume", headers=auth_headers
    )

    assert response.status_code == 404


def test_storage_failure_returns_503_and_creates_no_lead(
    client: TestClient, settings, db_session, emails
) -> None:
    """A1: a storage outage fails the request cleanly instead of half-creating a lead."""
    from app.core.deps import get_file_storage

    client.app.dependency_overrides[get_file_storage] = FailingStorage

    response = client.post("/api/v1/leads", data=lead_form(), files=resume_file())

    assert response.status_code == 503
    assert response.json()["code"] == "storage_unavailable"
    assert emails.sent == []


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("../../etc/passwd", "passwd"),
        ("/absolute/path/cv.pdf", "cv.pdf"),
        ("..\\..\\windows\\system32", "system32"),
        (".bashrc", "bashrc"),
        ("résumé.pdf", "r_sum_.pdf"),
        ("", "resume"),
    ],
)
def test_sanitise_filename_neutralises_traversal(raw: str, expected: str) -> None:
    """S2: an untrusted filename can never contain a path component."""
    assert sanitise_filename(raw) == expected


def test_local_storage_round_trip(tmp_path) -> None:
    """The disk adapter saves, reads back and deletes."""
    storage = LocalDiskStorage(root=tmp_path)
    key = build_key("cv.pdf")

    storage.save(key, io.BytesIO(b"bytes"), "application/pdf")
    assert storage.open(key).read() == b"bytes"

    storage.delete(key)
    with pytest.raises(FileNotFoundError):
        storage.open(key)


def test_local_storage_refuses_escaping_keys(tmp_path) -> None:
    """S2: even a hand-crafted key cannot write outside the storage root."""
    storage = LocalDiskStorage(root=tmp_path / "uploads")

    with pytest.raises(ValueError, match="outside the storage root"):
        storage.save("../escaped.pdf", io.BytesIO(b"x"), "application/pdf")
