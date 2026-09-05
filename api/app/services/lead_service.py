"""Lead intake business logic. Framework-free so it is testable without HTTP (M1)."""

import logging
import secrets
import uuid
from base64 import b32encode
from dataclasses import dataclass
from typing import BinaryIO

import filetype
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models.lead import Lead, LeadEvent, LeadState
from app.repositories.lead_repo import LeadRepository
from app.schemas.lead import LeadCreate
from app.services.email.base import EmailService
from app.services.email.messages import (
    LeadSnapshot,
    attorney_notification,
    prospect_confirmation,
    status_changed,
)
from app.services.exceptions import (
    InvalidTransition,
    LeadNotFound,
    ResumeTooLarge,
    StorageUnavailable,
    UnknownAssignee,
    UnsupportedResumeType,
)
from app.services.lead_state import assert_transition, rule_for
from app.services.storage.base import FileStorage
from app.services.storage.local import build_key

logger = logging.getLogger(__name__)

SYSTEM_ACTOR = "system"

# 160 bits of entropy, base32 without padding: unguessable, and safe to read aloud or
# paste into a form. Deliberately not derived from the lead id (SEC7).
_TRACKING_CODE_BYTES = 20

# Magic-byte signatures we accept, mapped to the extension they must agree with (SEC2).
# DOCX is a ZIP container, so the sniffer reports it as such.
_SIGNATURE_EXTENSIONS: dict[str, set[str]] = {
    "pdf": {".pdf"},
    "zip": {".docx"},
    "docx": {".docx"},
}


def generate_tracking_code() -> str:
    """Return a high-entropy, human-transcribable tracking code (EXT1)."""
    return b32encode(secrets.token_bytes(_TRACKING_CODE_BYTES)).decode().rstrip("=")


@dataclass(frozen=True)
class StateChange:
    """The outcome of a transition: the lead, and whether to tell the prospect.

    The decision belongs to the service (it reads the transition table); the
    *scheduling* belongs to the router, which owns BackgroundTasks. Returning it keeps
    that split honest instead of letting the router re-derive business rules.
    """

    lead: "Lead"
    notify_prospect: bool


@dataclass
class ResumeUpload:
    """A received file, decoupled from FastAPI's ``UploadFile`` (M1)."""

    filename: str
    content_type: str
    stream: BinaryIO


class LeadService:
    """Use cases for the lead intake pipeline."""

    def __init__(
        self,
        db: Session,
        repo: LeadRepository,
        storage: FileStorage,
        email: EmailService,
        settings: Settings,
    ) -> None:
        self._db = db
        self._repo = repo
        self._storage = storage
        self._email = email
        self._settings = settings

    # --- commands ------------------------------------------------------------

    def choose_assignee(self) -> str | None:
        """Pick the attorney with the fewest open leads (FR10).

        Ties break on roster order, which makes the choice deterministic and therefore
        testable -- and gives the first-listed attorney the first lead on a cold start,
        rather than an arbitrary one.

        Returns ``None`` when no roster is configured, in which case leads stay
        unassigned and notifications fall back to the shared inbox.
        """
        roster = [str(attorney.email).lower() for attorney in self._settings.attorneys]
        if not roster:
            return None

        counts = self._repo.open_lead_counts()
        # min() is stable, so the earliest roster entry wins a tie.
        return min(roster, key=lambda email: counts.get(email, 0))

    def create_lead(self, data: LeadCreate, upload: ResumeUpload) -> Lead:
        """Validate the upload, store the file, then persist the lead (FR1).

        Ordering matters: the file lands first so a storage outage fails the request
        before a lead row exists (A1). The DB transaction is committed here so the
        caller can schedule email only after durable success (R1).
        """
        self._validate_upload(upload)

        key = build_key(upload.filename)
        try:
            self._storage.save(key, upload.stream, upload.content_type)
        except Exception as exc:  # noqa: BLE001 - adapter-agnostic by design
            logger.exception("Storage rejected resume for key %s", key)
            raise StorageUnavailable("Could not store the uploaded resume.") from exc

        lead = Lead(
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            resume_key=key,
            resume_filename=upload.filename,
            resume_content_type=upload.content_type,
            state=LeadState.PENDING,
            tracking_code=generate_tracking_code(),
            # Chosen before the insert so the owner is set atomically with the lead
            # itself: a submission is never briefly ownerless (FR10).
            assigned_to=self.choose_assignee(),
        )

        try:
            self._repo.create(lead)
            # Same transaction as the insert, so the trail can never disagree (SEC9).
            self._repo.add_event(
                lead_id=lead.id,
                from_state=None,
                to_state=LeadState.PENDING,
                actor=SYSTEM_ACTOR,
                to_assignee=lead.assigned_to,
            )
            self._db.commit()
        except Exception:
            self._db.rollback()
            # Nothing references the object now, so leaving it would be a silent leak.
            self._storage.delete(key)
            raise

        self._db.refresh(lead)
        return lead

    def change_state(self, lead_id: uuid.UUID, new_state: LeadState, actor: str) -> StateChange:
        """Move a lead to ``new_state`` if the transition table allows it (FR8/FR9).

        Two guards, deliberately: ``assert_transition`` is a fast in-process check that
        produces the human-readable message and distinguishes "already there" from
        "illegal move", but it is only advisory -- between its SELECT and the UPDATE
        another request can change the row. The SQL predicate in ``update_state`` is
        the source of truth, so exactly one of N concurrent callers can win (R2).
        """
        lead = self.get_lead(lead_id)
        assert_transition(lead.state, new_state)
        previous = lead.state

        if not self._repo.update_state(lead.id, previous, new_state):
            self._db.rollback()
            raise InvalidTransition(
                f"Cannot move a lead from {previous} to {new_state}; "
                "it was changed by another request."
            )

        self._repo.add_event(lead_id=lead.id, from_state=previous, to_state=new_state, actor=actor)
        self._db.commit()
        self._db.refresh(lead)

        rule = rule_for(previous, new_state)
        return StateChange(lead=lead, notify_prospect=bool(rule and rule.notify_prospect))

    def assign_lead(
        self, lead_id: uuid.UUID, assignee: str | None, actor: str, roster: set[str]
    ) -> Lead:
        """Assign a lead to an attorney, or clear the assignment (FR10).

        Idempotent by design: asking for the assignee a lead already has is a no-op
        that returns 200 and writes no audit row. Repeating a click, or two tabs
        submitting the same claim, is not an error worth showing anyone -- unlike a
        *state* change, where a repeat means the caller was looking at stale data.

        :raises UnknownAssignee: if ``assignee`` is not on the configured roster.
        """
        if assignee is not None and assignee.lower() not in roster:
            raise UnknownAssignee(f"{assignee} is not a configured attorney.")

        target = assignee.lower() if assignee else None
        lead = self.get_lead(lead_id)
        previous = lead.assigned_to

        if previous == target:
            return lead

        if not self._repo.update_assignee(lead.id, previous, target):
            # Someone else claimed it between the read and the write.
            self._db.rollback()
            raise UnknownAssignee(
                "That lead was assigned by someone else just now. Refresh and try again."
            )

        # Same transaction as the update, so the trail cannot disagree (SEC9).
        self._repo.add_event(
            lead_id=lead.id,
            from_state=lead.state,
            to_state=lead.state,
            actor=actor,
            from_assignee=previous,
            to_assignee=target,
        )
        self._db.commit()
        self._db.refresh(lead)
        return lead

    # --- queries -------------------------------------------------------------

    def get_lead(self, lead_id: uuid.UUID) -> Lead:
        """Return a lead or raise :class:`LeadNotFound`."""
        lead = self._repo.get(lead_id)
        if lead is None:
            raise LeadNotFound(f"No lead with id {lead_id}.")
        return lead

    def public_status(self, tracking_code: str) -> tuple[Lead, list[LeadEvent]]:
        """Look a lead up by its public tracking code (EXT1).

        The comparison is constant-time so response timing cannot be used to confirm
        that a guessed prefix is on the right track, and the not-found error carries no
        hint about whether the code was well-formed (SEC7). With 160 bits of entropy
        guessing is infeasible anyway; this closes the cheap side channel too.
        """
        candidate = (tracking_code or "").strip().upper()
        lead = self._repo.get_by_tracking_code(candidate) if candidate else None

        if lead is None or not secrets.compare_digest(lead.tracking_code, candidate):
            # Same message and shape for malformed, unknown and empty codes.
            raise LeadNotFound("No submission matches that tracking code.")

        return lead, self._repo.list_events(lead.id)

    def get_lead_with_events(self, lead_id: uuid.UUID) -> tuple[Lead, list[LeadEvent]]:
        """Return a lead and its audit trail (SEC9)."""
        lead = self.get_lead(lead_id)
        return lead, self._repo.list_events(lead.id)

    def list_leads(
        self,
        state: LeadState | None,
        limit: int,
        offset: int,
        assigned_to: str | None = None,
        unassigned_only: bool = False,
    ) -> tuple[list[Lead], int]:
        """Return one page of leads plus the total count (FR5/FR10)."""
        return self._repo.list(
            state=state,
            assigned_to=assigned_to,
            unassigned_only=unassigned_only,
            limit=limit,
            offset=offset,
        )

    def open_resume(self, lead: Lead) -> BinaryIO:
        """Open the stored resume for streaming (FR6)."""
        try:
            return self._storage.open(lead.resume_key)
        except FileNotFoundError as exc:
            raise LeadNotFound(f"The resume for lead {lead.id} is no longer available.") from exc

    def resume_url(self, lead: Lead, expires: int = 300) -> str | None:
        """A presigned direct URL when the backend supports one, else ``None`` (E2)."""
        return self._storage.presigned_url(lead.resume_key, expires=expires)

    # --- notifications -------------------------------------------------------

    def send_status_change_email(self, lead: LeadSnapshot) -> None:
        """Tell the prospect their status moved (EXT2).

        Same shape and same guarantees as the intake emails: a detached snapshot,
        scheduled after the transaction commits, and provider failures logged rather
        than raised. The price is the same too -- at-most-once delivery, which is why
        DESIGN.md names the transactional outbox as the fix.
        """
        message = status_changed(lead, self._settings.status_portal_url)
        if message is None:
            logger.info("No prospect copy for state %s; not sending", lead.state)
            return

        try:
            self._email.send(
                to=message.to,
                subject=message.subject,
                text=message.text,
                html=message.html,
                lead_id=lead.id,
                cc=message.cc,
                reply_to=message.reply_to,
            )
        except Exception:  # noqa: BLE001 - a broken provider must not surface here
            logger.exception("Failed to send the status update for lead_id=%s", lead.id)

    def send_intake_emails(self, lead: LeadSnapshot) -> None:
        """Send prospect confirmation and attorney notification (FR2/FR3).

        Takes a detached snapshot rather than the ORM instance: this runs in a
        background task after the request's session has closed, so touching a live
        model here would be a latent lazy-load error.

        Provider failures are logged and swallowed -- the lead is already committed and
        must not be lost because email broke (R1). The price is at-most-once delivery;
        the upgrade is a transactional outbox, noted in DESIGN.md.
        """
        # The owning attorney gets the notification directly; the shared inbox is the
        # fallback for an unassigned lead, which only happens with an empty roster.
        notify_email = lead.assigned_to or self._settings.attorney_notify_email
        messages = (
            prospect_confirmation(lead, self._settings.status_portal_url),
            attorney_notification(
                lead,
                notify_email=notify_email,
                internal_ui_url=self._settings.internal_ui_url,
            ),
        )
        for message in messages:
            try:
                self._email.send(
                    to=message.to,
                    subject=message.subject,
                    text=message.text,
                    html=message.html,
                    lead_id=lead.id,
                    cc=message.cc,
                    reply_to=message.reply_to,
                )
            except Exception:  # noqa: BLE001 - a broken provider must not surface here
                logger.exception("Failed to send %r for lead_id=%s", message.subject, lead.id)

    # --- internals -----------------------------------------------------------

    def _validate_upload(self, upload: ResumeUpload) -> None:
        """Enforce the upload allow-list and size cap (S2/SEC2).

        Three things must agree: the declared content type, the file extension, and the
        actual leading bytes. Checking only the first two lets an executable through
        simply by renaming it, which is exactly what the P0 audit demonstrated.
        """
        settings = self._settings

        if upload.content_type not in settings.allowed_resume_content_types:
            raise UnsupportedResumeType(
                f"Resume type {upload.content_type!r} is not accepted. "
                f"Allowed: {', '.join(settings.allowed_resume_extensions)}."
            )

        suffix = f".{upload.filename.rsplit('.', 1)[-1].lower()}" if "." in upload.filename else ""
        if suffix not in settings.allowed_resume_extensions:
            raise UnsupportedResumeType(
                f"Resume extension {suffix or '(none)'} is not accepted. "
                f"Allowed: {', '.join(settings.allowed_resume_extensions)}."
            )

        size = self._measure(upload.stream)
        if size > settings.max_resume_bytes:
            raise ResumeTooLarge(f"Resume exceeds the {settings.max_resume_mb} MB limit.")
        if size == 0:
            raise UnsupportedResumeType("The uploaded resume is empty.")

        self._assert_magic_bytes_match(upload, suffix)

    @staticmethod
    def _assert_magic_bytes_match(upload: ResumeUpload, suffix: str) -> None:
        """Reject a file whose real type disagrees with its name (SEC2).

        Content sniffing is not a malware scanner -- a valid PDF can still be hostile.
        It closes the trivial "rename evil.exe to cv.pdf" path; AV scanning is the next
        layer and is named in DESIGN.md.
        """
        header = upload.stream.read(261)
        upload.stream.seek(0)

        kind = filetype.guess(header)
        if kind is None:
            raise UnsupportedResumeType(
                "That file does not look like a PDF or DOCX. Please upload a real document."
            )

        allowed = _SIGNATURE_EXTENSIONS.get(kind.extension, set())
        if suffix not in allowed:
            raise UnsupportedResumeType(
                f"The file contents look like {kind.extension!r}, which does not match "
                f"the {suffix} extension."
            )

    @staticmethod
    def _measure(stream: BinaryIO) -> int:
        """Return the stream length and rewind it, without reading it into memory."""
        stream.seek(0, 2)
        size = stream.tell()
        stream.seek(0)
        return size
