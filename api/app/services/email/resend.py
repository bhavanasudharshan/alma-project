"""Resend email adapter (P1), selected when ``RESEND_API_KEY`` is set."""

import logging

import resend

from app.core.config import Settings

logger = logging.getLogger(__name__)


class ResendEmailService:
    """Sends through Resend, sending HTML with a plain-text fallback part."""

    def __init__(self, settings: Settings) -> None:
        resend.api_key = settings.resend_api_key
        self._from = settings.email_from

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
        """Send one message.

        Provider errors are logged with the lead id and swallowed: the lead is already
        committed, and a failed notification must never turn into a failed request or a
        lost submission (R1). The price is at-most-once delivery, which the outbox
        pattern in DESIGN.md is the fix for.
        """
        params: resend.Emails.SendParams = {
            "from": self._from,
            "to": [to],
            "subject": subject,
            "text": text,
        }
        if html:
            params["html"] = html
        if cc:
            params["cc"] = cc
        if reply_to:
            params["reply_to"] = reply_to

        try:
            result = resend.Emails.send(params)
            logger.info(
                "EMAIL (resend) to=%s subject=%r lead_id=%s provider_id=%s",
                to,
                subject,
                lead_id or "-",
                (result or {}).get("id", "-"),
            )
        except Exception:  # noqa: BLE001 - any provider failure is non-fatal here
            logger.exception(
                "Resend failed for lead_id=%s to=%s subject=%r", lead_id or "-", to, subject
            )
