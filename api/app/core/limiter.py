"""Per-IP rate limiting for the public surface (SEC1).

In-memory storage is correct for a single process and is what the reviewer run uses.

This is the one piece of per-process state in the service, and it is worth saying out
loud: the API is stateless *except* for these counters. Two replicas with in-memory
storage therefore grant roughly double the intended budget -- the limit degrades, it
does not fail open entirely. Pointing ``RATE_LIMIT_STORAGE_URL`` at Redis makes the
counters shared and the service genuinely stateless (P2).
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import get_settings

_settings = get_settings()

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=_settings.rate_limit_storage_url,
    enabled=_settings.rate_limit_enabled,
)


def leads_limit() -> str:
    """Submission limit, e.g. ``5/10minutes``."""
    return get_settings().rate_limit_leads


def login_limit() -> str:
    """Login attempt limit, e.g. ``10/5minutes``."""
    return get_settings().rate_limit_login


def status_limit() -> str:
    """Public status lookup limit, e.g. ``20/minute`` (EXT1/SEC7)."""
    return get_settings().rate_limit_status
