"""In-memory adapters used by the whole suite.

CLAUDE.md forbids touching real providers in tests; these are fakes (working
implementations) rather than mocks, so the assertions are about behaviour (M2).
"""

import io
from typing import BinaryIO


class FakeStorage:
    """:class:`FileStorage` backed by a dict, so no test writes to disk."""

    def __init__(self) -> None:
        self.saved: dict[str, bytes] = {}
        self.content_types: dict[str, str] = {}

    def save(self, key: str, fileobj: BinaryIO, content_type: str) -> None:
        self.saved[key] = fileobj.read()
        self.content_types[key] = content_type

    def open(self, key: str) -> BinaryIO:
        if key not in self.saved:
            raise FileNotFoundError(key)
        return io.BytesIO(self.saved[key])

    def delete(self, key: str) -> None:
        self.saved.pop(key, None)
        self.content_types.pop(key, None)


class FailingStorage:
    """Storage adapter that always fails, for the degrade-gracefully path (A1)."""

    def save(self, key: str, fileobj: BinaryIO, content_type: str) -> None:
        raise OSError("disk on fire")

    def open(self, key: str) -> BinaryIO:
        raise FileNotFoundError(key)

    def delete(self, key: str) -> None:
        return None


class FakeEmailService:
    """:class:`EmailService` that records messages instead of sending them."""

    def __init__(self) -> None:
        self.sent: list[dict[str, str | None]] = []

    def send(self, to: str, subject: str, text: str, html: str | None = None) -> None:
        self.sent.append({"to": to, "subject": subject, "text": text, "html": html})

    @property
    def recipients(self) -> list[str]:
        """Addresses in send order."""
        return [message["to"] for message in self.sent]
