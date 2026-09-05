"""The email port. Console in P0, Resend in P1, fakes in tests -- one interface (E2)."""

from typing import Protocol


class EmailService(Protocol):
    """Transactional email sender."""

    def send(self, to: str, subject: str, text: str, html: str | None = None) -> None:
        """Deliver one message.

        Implementations must not raise for provider-side failures: a lost email must
        never lose a lead (R1). Log and return instead.
        """
        ...
