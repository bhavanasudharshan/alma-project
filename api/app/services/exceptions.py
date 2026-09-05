"""Domain errors.

Pure Python: services must never import FastAPI (CLAUDE.md layering). The HTTP
mapping lives in ``app/api/errors.py``, which is the only place that knows status
codes. Each error carries a stable machine-readable ``code`` for the response
envelope ``{"detail": ..., "code": ...}`` (M6).
"""


class DomainError(Exception):
    """Base class for expected, client-visible failures."""

    code = "domain_error"

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class LeadNotFound(DomainError):
    """No lead exists with the requested id."""

    code = "lead_not_found"


class InvalidTransition(DomainError):
    """The requested lead state change is not allowed by the transition table (FR9)."""

    code = "invalid_transition"


class AlreadyInState(DomainError):
    """The lead is already in the requested state.

    Distinct from :class:`InvalidTransition` so a client can tell "nothing to do" apart
    from "that move is illegal". Both are HTTP 409; only this one is benign.
    """

    code = "already_in_state"


class UnsupportedResumeType(DomainError):
    """Upload rejected by the content-type / extension allow-list (S2)."""

    code = "unsupported_media_type"


class ResumeTooLarge(DomainError):
    """Upload exceeded ``settings.max_resume_mb`` (S2)."""

    code = "resume_too_large"


class StorageUnavailable(DomainError):
    """The storage backend could not accept the file; the lead is not created (A1)."""

    code = "storage_unavailable"


class InvalidCredentials(DomainError):
    """Login failed. Deliberately does not say which half was wrong (S4)."""

    code = "invalid_credentials"
