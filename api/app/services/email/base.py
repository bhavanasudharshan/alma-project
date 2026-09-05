"""The email port. Console, Resend and test fakes all satisfy it (E2)."""

from typing import Protocol


class EmailService(Protocol):
    """Transactional email sender."""

    def send(
        self,
        to: str,
        subject: str,
        text: str,
        html: str | None = None,
        lead_id: str | None = None,
    ) -> None:
        """Deliver one message.

        ``lead_id`` is for correlation in logs only -- it lets a provider failure be
        traced back to a lead without writing the prospect's details into the log (C1).

        Implementations must not raise for provider-side failures: a lost email must
        never lose a lead (R1). Log and return instead.
        """
        ...
