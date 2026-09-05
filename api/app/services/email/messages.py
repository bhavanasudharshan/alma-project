"""Message bodies for the lead-intake emails (FR2/FR3).

Both a plain-text and an HTML part are produced. HTML is rendered through Jinja2 with
autoescape on, because every value here is prospect-supplied: a name containing
``<script>`` must arrive as text in the attorney's inbox, not as markup (SEC3).
"""

from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

TEMPLATE_DIR = Path(__file__).parent / "templates"

_env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(["html", "xml", "j2"], default_for_string=True),
    trim_blocks=True,
    lstrip_blocks=True,
)


def _single_line(value: str) -> str:
    """Collapse CR/LF so a crafted name cannot inject extra headers (SEC3).

    A subject line is a header. Newlines in one are how header injection works, so they
    are removed rather than escaped.
    """
    return " ".join(value.replace("\r", " ").replace("\n", " ").split())


@dataclass(frozen=True)
class EmailMessage:
    """A rendered message ready to hand to an :class:`EmailService`."""

    to: str
    subject: str
    text: str
    html: str | None = None


@dataclass(frozen=True)
class LeadSnapshot:
    """A detached, plain copy of the lead fields the emails need.

    Background tasks run after the request's DB session is closed, so handing them a
    live ORM instance depends on ``expire_on_commit=False`` and breaks the moment a
    lazy attribute is touched. A frozen snapshot has no session affinity at all.
    """

    id: str
    first_name: str
    last_name: str
    email: str
    resume_filename: str
    resume_content_type: str
    state: str
    tracking_code: str
    received_at: str

    @classmethod
    def from_lead(cls, lead) -> "LeadSnapshot":  # noqa: ANN001 - avoids a db import here
        """Copy the fields off an ORM instance while its session is still open."""
        return cls(
            id=str(lead.id),
            first_name=lead.first_name,
            last_name=lead.last_name,
            email=lead.email,
            resume_filename=lead.resume_filename,
            resume_content_type=lead.resume_content_type,
            state=str(lead.state),
            tracking_code=lead.tracking_code,
            received_at=lead.created_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
        )


def prospect_confirmation(lead: LeadSnapshot, status_portal_url: str = "") -> EmailMessage:
    """Confirmation sent to the prospect who submitted the form (FR2/EXT1)."""
    text = (
        f"Hi {lead.first_name},\n\n"
        "Thanks for submitting your information. An attorney will review your "
        "background and reach out to you directly about next steps.\n\n"
        "What we received:\n"
        f"  Name:   {lead.first_name} {lead.last_name}\n"
        f"  Email:  {lead.email}\n"
        f"  Resume: {lead.resume_filename}\n\n"
        f"Your tracking code: {lead.tracking_code}\n"
        + (
            f"Check your status any time: {status_portal_url}\n\n"
            if status_portal_url
            else "Keep it — you will be able to check your status with it.\n\n"
        )
        + "No action is needed from you right now.\n\n"
        "— Alma"
    )
    html = _env.get_template("prospect_confirmation.html.j2").render(
        first_name=lead.first_name,
        last_name=lead.last_name,
        email=lead.email,
        resume_filename=lead.resume_filename,
        tracking_code=lead.tracking_code,
        status_portal_url=status_portal_url,
    )
    return EmailMessage(
        to=lead.email,
        subject=_single_line("We received your information"),
        text=text,
        html=html,
    )


# What the prospect is told for each state they can be moved into (EXT2). Adding a
# state means adding a row here; a missing row simply means no email is sent.
_STATUS_COPY: dict[str, tuple[str, str]] = {
    "REACHED_OUT": (
        "An attorney has reviewed your submission and is reaching out to you.",
        "Look out for an email from our team about next steps. You do not need to do "
        "anything right now.",
    ),
    "QUALIFIED": (
        "Good news — an attorney has assessed your background as a strong fit.",
        "Your case is moving forward. An attorney will be in touch about what happens "
        "next and what they need from you.",
    ),
}


def status_changed(lead: LeadSnapshot, status_portal_url: str = "") -> EmailMessage | None:
    """Tell the prospect their status moved (EXT2).

    Returns ``None`` for a state with no copy, so a new state added to the transition
    table cannot accidentally send an empty or confusing email -- silence is the safe
    default until someone writes the words.
    """
    copy = _STATUS_COPY.get(lead.state)
    if copy is None:
        return None
    headline, detail = copy

    text_lines = [f"Hi {lead.first_name},", "", headline, "", detail, ""]
    if status_portal_url:
        text_lines += [
            f"Check your status any time: {status_portal_url}",
            f"Your tracking code: {lead.tracking_code}",
            "",
        ]
    text_lines += ["— Alma"]

    html = _env.get_template("status_changed.html.j2").render(
        first_name=lead.first_name,
        headline=headline,
        detail=detail,
        tracking_code=lead.tracking_code,
        status_portal_url=status_portal_url,
    )
    return EmailMessage(
        to=lead.email,
        subject=_single_line("An update on your submission"),
        text="\n".join(text_lines),
        html=html,
    )


def attorney_notification(
    lead: LeadSnapshot, notify_email: str, internal_ui_url: str
) -> EmailMessage:
    """Notification sent to the attorney inbox with the full lead detail (FR3)."""
    text = (
        "A new lead was submitted.\n\n"
        f"  Name:     {lead.first_name} {lead.last_name}\n"
        f"  Email:    {lead.email}\n"
        f"  Resume:   {lead.resume_filename} ({lead.resume_content_type})\n"
        f"  State:    {lead.state}\n"
        f"  Received: {lead.received_at}\n\n"
        f"Open the intake queue: {internal_ui_url}\n"
    )
    html = _env.get_template("attorney_notification.html.j2").render(
        first_name=lead.first_name,
        last_name=lead.last_name,
        email=lead.email,
        resume_filename=lead.resume_filename,
        resume_content_type=lead.resume_content_type,
        state=lead.state,
        received_at=lead.received_at,
        internal_ui_url=internal_ui_url,
    )
    return EmailMessage(
        to=notify_email,
        subject=_single_line(f"New lead: {lead.first_name} {lead.last_name}"),
        text=text,
        html=html,
    )
