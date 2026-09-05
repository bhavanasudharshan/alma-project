"""Message bodies for the two lead-intake emails (FR2/FR3).

Plain text only in P0; HTML templates arrive in P1. Kept separate from the adapters
so the wording is testable without a provider.
"""

from dataclasses import dataclass

from app.db.models.lead import Lead


@dataclass(frozen=True)
class EmailMessage:
    """A rendered message ready to hand to an :class:`EmailService`."""

    to: str
    subject: str
    text: str


def prospect_confirmation(lead: Lead) -> EmailMessage:
    """Confirmation sent to the prospect who submitted the form (FR2)."""
    text = (
        f"Hi {lead.first_name},\n\n"
        "Thanks for submitting your information. An attorney will review your "
        "background and reach out to you directly about next steps.\n\n"
        "What we received:\n"
        f"  Name:   {lead.first_name} {lead.last_name}\n"
        f"  Email:  {lead.email}\n"
        f"  Resume: {lead.resume_filename}\n\n"
        "No action is needed from you right now.\n\n"
        "— Alma"
    )
    return EmailMessage(to=lead.email, subject="We received your information", text=text)


def attorney_notification(lead: Lead, notify_email: str, internal_ui_url: str) -> EmailMessage:
    """Notification sent to the attorney inbox with the full lead detail (FR3)."""
    text = (
        "A new lead was submitted.\n\n"
        f"  Name:     {lead.first_name} {lead.last_name}\n"
        f"  Email:    {lead.email}\n"
        f"  Resume:   {lead.resume_filename} ({lead.resume_content_type})\n"
        f"  State:    {lead.state}\n"
        f"  Received: {lead.created_at:%Y-%m-%d %H:%M:%S %Z}\n\n"
        f"Open the intake queue: {internal_ui_url}\n"
    )
    subject = f"New lead: {lead.first_name} {lead.last_name}"
    return EmailMessage(to=notify_email, subject=subject, text=text)
