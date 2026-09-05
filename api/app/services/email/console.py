"""Console email adapter: the P0/P1 default so reviewers need no provider account ($1)."""

import logging

logger = logging.getLogger(__name__)


class ConsoleEmailService:
    """Writes messages to the log instead of sending them.

    Resumes and the details around them are PII (C1), and application logs are widely
    readable and long-lived. INFO therefore carries only what is needed to confirm the
    send happened -- recipient, subject, lead id -- while the rendered body, which
    repeats the prospect's details back, is emitted at DEBUG.
    """

    def send(
        self,
        to: str,
        subject: str,
        text: str,
        html: str | None = None,
        lead_id: str | None = None,
        cc: list[str] | None = None,
        reply_to: str | None = None,
    ) -> None:
        """Log the message. Never raises (R1)."""
        logger.info(
            "EMAIL (console) to=%s cc=%s reply_to=%s subject=%r lead_id=%s",
            to,
            ",".join(cc) if cc else "-",
            reply_to or "-",
            subject,
            lead_id or "-",
        )
        logger.debug("EMAIL (console) body for lead_id=%s:\n%s", lead_id or "-", text)
