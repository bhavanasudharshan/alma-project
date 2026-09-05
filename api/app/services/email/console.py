"""Console email adapter: the P0 default so reviewers need no provider account ($1)."""

import logging

logger = logging.getLogger(__name__)


class ConsoleEmailService:
    """Writes the full message to the log at INFO instead of sending it."""

    def send(self, to: str, subject: str, text: str, html: str | None = None) -> None:
        """Log the message. Never raises (R1)."""
        logger.info(
            "EMAIL (console)\n  to: %s\n  subject: %s\n  body:\n%s",
            to,
            subject,
            text,
        )
