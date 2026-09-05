"""Lead intake business logic. Framework-free so it is testable without HTTP (M1)."""

import logging
import uuid
from dataclasses import dataclass
from typing import BinaryIO

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models.lead import Lead, LeadState
from app.repositories.lead_repo import LeadRepository
from app.schemas.lead import LeadCreate
from app.services.email.base import EmailService
from app.services.email.messages import attorney_notification, prospect_confirmation
from app.services.exceptions import (
    InvalidTransition,
    LeadNotFound,
    ResumeTooLarge,
    StorageUnavailable,
    UnsupportedResumeType,
)
from app.services.lead_state import assert_transition
from app.services.storage.base import FileStorage
from app.services.storage.local import build_key

logger = logging.getLogger(__name__)


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
        )

        try:
            self._repo.create(lead)
            self._db.commit()
        except Exception:
            self._db.rollback()
            # Nothing references the object now, so leaving it would be a silent leak.
            self._storage.delete(key)
            raise

        self._db.refresh(lead)
        return lead

    def change_state(self, lead_id: uuid.UUID, new_state: LeadState) -> Lead:
        """Move a lead to ``new_state`` if the transition table allows it (FR8/FR9).

        Two guards, deliberately: ``assert_transition`` is a fast in-process check that
        produces the human-readable message, but it is only advisory -- between its
        SELECT and the UPDATE another request can change the row. The SQL predicate in
        ``update_state`` is the source of truth, so exactly one of N concurrent callers
        can win and the rest get a 409 (R2).
        """
        lead = self.get_lead(lead_id)
        assert_transition(lead.state, new_state)

        if not self._repo.update_state(lead.id, lead.state, new_state):
            self._db.rollback()
            raise InvalidTransition(
                f"Cannot move a lead from {lead.state} to {new_state}; "
                "it was changed by another request."
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

    def list_leads(
        self, state: LeadState | None, limit: int, offset: int
    ) -> tuple[list[Lead], int]:
        """Return one page of leads plus the total count (FR5)."""
        return self._repo.list(state=state, limit=limit, offset=offset)

    def open_resume(self, lead: Lead) -> BinaryIO:
        """Open the stored resume for streaming (FR6)."""
        try:
            return self._storage.open(lead.resume_key)
        except FileNotFoundError as exc:
            raise LeadNotFound(f"The resume for lead {lead.id} is no longer available.") from exc

    # --- notifications -------------------------------------------------------

    def send_intake_emails(self, lead: Lead) -> None:
        """Send prospect confirmation and attorney notification (FR2/FR3).

        Runs in a background task after the response is returned. Provider failures
        are logged and swallowed: the lead is already committed and must not be lost
        because email broke (R1). The price is at-most-once delivery -- the upgrade
        is a transactional outbox, noted in DESIGN.md.
        """
        messages = (
            prospect_confirmation(lead),
            attorney_notification(
                lead,
                notify_email=self._settings.attorney_notify_email,
                internal_ui_url=self._settings.internal_ui_url,
            ),
        )
        for message in messages:
            try:
                self._email.send(to=message.to, subject=message.subject, text=message.text)
            except Exception:  # noqa: BLE001 - a broken provider must not surface here
                logger.exception("Failed to send %r to %s", message.subject, message.to)

    # --- internals -----------------------------------------------------------

    def _validate_upload(self, upload: ResumeUpload) -> None:
        """Enforce the upload allow-list and size cap (S2).

        Both the declared content type and the file extension must be allowed; a
        mismatch between them is still rejected. Content sniffing and virus scanning
        are the next layer and are deliberately out of scope here.
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

    @staticmethod
    def _measure(stream: BinaryIO) -> int:
        """Return the stream length and rewind it, without reading it into memory."""
        stream.seek(0, 2)
        size = stream.tell()
        stream.seek(0)
        return size
