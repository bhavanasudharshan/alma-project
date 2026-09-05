"""Lead routes. No business logic here -- routers validate, delegate, and shape output."""

import logging
import uuid
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, File, Form, Query, Request, UploadFile, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import Response, StreamingResponse
from pydantic import ValidationError

from app.core.deps import AttorneyDep, LeadServiceDep
from app.core.limiter import leads_limit, limiter, status_limit
from app.db.models.lead import LeadState
from app.schemas.lead import (
    LeadCreate,
    LeadDetail,
    LeadEventRead,
    LeadListResponse,
    LeadRead,
    LeadStateUpdate,
    PublicLeadStatus,
    PublicStatusEvent,
)
from app.services.email.messages import LeadSnapshot
from app.services.lead_service import ResumeUpload
from app.services.storage.local import display_filename

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/leads", tags=["leads"])


@router.post(
    "",
    response_model=LeadRead,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a lead (public)",
    responses={
        413: {"description": "Resume exceeds the size limit"},
        415: {"description": "Resume type not accepted"},
        202: {"description": "Accepted and silently discarded (honeypot triggered)"},
        422: {"description": "Invalid form fields"},
        429: {"description": "Too many submissions from this address"},
        503: {"description": "Resume storage unavailable"},
    },
)
@limiter.limit(leads_limit)
def create_lead(
    request: Request,
    background_tasks: BackgroundTasks,
    service: LeadServiceDep,
    first_name: Annotated[str, Form(max_length=100)],
    last_name: Annotated[str, Form(max_length=100)],
    email: Annotated[str, Form(max_length=320)],
    resume: Annotated[UploadFile, File()],
    website: Annotated[str, Form(max_length=200)] = "",
) -> LeadRead | Response:
    """Create a lead from the public form (FR1).

    Emails are scheduled only after ``create_lead`` has committed, so a provider
    outage can never roll back or fail an accepted submission (R1).

    ``website`` is a honeypot (SEC4): it is hidden from people and left empty by real
    browsers, so anything in it means a bot. Those get a 202 and nothing is stored --
    answering normally denies the bot the signal it would use to adapt.
    """
    if website.strip():
        client = request.client.host if request.client else "-"
        logger.info("Dropped a honeypot submission from %s", client)
        # Returning a Response directly bypasses response_model validation, which is
        # what lets this path answer without a lead body.
        return Response(status_code=status.HTTP_202_ACCEPTED)

    # Multipart fields arrive as plain strings, so the model is built by hand here;
    # re-raising as RequestValidationError keeps the 422 envelope identical to the
    # one FastAPI produces for JSON bodies (M6).
    try:
        data = LeadCreate(first_name=first_name, last_name=last_name, email=email)
    except ValidationError as exc:
        raise RequestValidationError(exc.errors()) from exc

    upload = ResumeUpload(
        filename=resume.filename or "resume",
        content_type=resume.content_type or "application/octet-stream",
        stream=resume.file,
    )

    lead = service.create_lead(data, upload)
    # A detached snapshot: the session is closed by the time the task runs.
    background_tasks.add_task(service.send_intake_emails, LeadSnapshot.from_lead(lead))
    return LeadRead.model_validate(lead)


@router.get(
    "",
    response_model=LeadListResponse,
    summary="List leads, newest first (attorney only)",
)
def list_leads(
    _: AttorneyDep,
    service: LeadServiceDep,
    state: Annotated[LeadState | None, Query(description="Filter by lead state")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> LeadListResponse:
    """Return one page of leads with the total matching count (FR5)."""
    items, total = service.list_leads(state=state, limit=limit, offset=offset)
    return LeadListResponse(
        items=[LeadRead.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


# Declared before "/{lead_id}" on purpose: FastAPI matches in order, and otherwise
# "track" would be captured by the UUID path parameter and 422.
@router.get(
    "/track/{tracking_code}",
    response_model=PublicLeadStatus,
    summary="Check a submission's status with its tracking code (public)",
    responses={
        404: {"description": "No submission matches that code"},
        429: {"description": "Too many lookups from this address"},
    },
)
@limiter.limit(status_limit)
def track_lead(request: Request, tracking_code: str, service: LeadServiceDep) -> PublicLeadStatus:
    """Return the prospect-visible status for a tracking code (EXT1).

    Public and unauthenticated, so the payload is state and timestamps only -- never
    name, email, resume or the internal lead id (SEC7). Rate limited per IP.
    """
    lead, events = service.public_status(tracking_code)
    return PublicLeadStatus(
        state=lead.state,
        submitted_at=lead.created_at,
        updated_at=lead.updated_at,
        events=[
            PublicStatusEvent(to_state=event.to_state, at=event.created_at) for event in events
        ],
    )


@router.get(
    "/{lead_id}",
    response_model=LeadDetail,
    summary="Fetch one lead with its audit trail (attorney only)",
    responses={404: {"description": "No such lead"}},
)
def get_lead(lead_id: uuid.UUID, _: AttorneyDep, service: LeadServiceDep) -> LeadDetail:
    """Return a single lead, its state history (SEC9) and a presigned URL if available."""
    lead, events = service.get_lead_with_events(lead_id)
    detail = LeadDetail.model_validate(lead)
    detail.events = [LeadEventRead.model_validate(event) for event in events]
    detail.resume_url = service.resume_url(lead)
    return detail


@router.get(
    "/{lead_id}/resume",
    summary="Download a lead's resume (attorney only)",
    responses={
        200: {"content": {"application/octet-stream": {}}},
        404: {"description": "No such lead or resume"},
    },
)
def download_resume(
    lead_id: uuid.UUID, _: AttorneyDep, service: LeadServiceDep
) -> StreamingResponse:
    """Stream the stored resume back under its original filename (FR6).

    The bytes are proxied rather than exposed as a public URL, so resumes stay behind
    authentication regardless of the storage backend (S1/C1).
    """
    lead = service.get_lead(lead_id)
    stream = service.open_resume(lead)

    # The stored filename is attacker-supplied, so it is flattened to a basename before
    # being echoed back: quote() defaults to safe="/", which would otherwise let
    # "../../etc/passwd.pdf" reach the client verbatim (S2). safe="" encodes the rest,
    # and display_filename keeps Unicode so accented names survive.
    download_name = display_filename(lead.resume_filename)
    disposition = f"attachment; filename*=UTF-8''{quote(download_name, safe='')}"
    return StreamingResponse(
        stream,
        media_type=lead.resume_content_type,
        headers={
            "Content-Disposition": disposition,
            # SEC2(c): never let a browser re-interpret an uploaded file's type.
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.patch(
    "/{lead_id}/state",
    response_model=LeadRead,
    summary="Change a lead's state (attorney only)",
    responses={
        404: {"description": "No such lead"},
        409: {"description": "Illegal state transition"},
    },
)
def update_lead_state(
    lead_id: uuid.UUID,
    payload: LeadStateUpdate,
    attorney: AttorneyDep,
    service: LeadServiceDep,
    background_tasks: BackgroundTasks,
) -> LeadRead:
    """Move a lead through the intake pipeline (FR8).

    409 ``already_in_state`` when it is already there, 409 ``invalid_transition`` for a
    move the pipeline forbids (FR9). The attorney is recorded in the audit trail.

    When the transition rule says so, the prospect is emailed after the commit -- same
    ordering as intake, so a provider outage can never undo an accepted change (R1).
    """
    change = service.change_state(lead_id, payload.state, actor=attorney)

    if change.notify_prospect:
        background_tasks.add_task(
            service.send_status_change_email, LeadSnapshot.from_lead(change.lead)
        )

    return LeadRead.model_validate(change.lead)
