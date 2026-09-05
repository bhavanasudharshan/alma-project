"""Health router (M5: liveness now, DB check added in P1)."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness probe. Returns ``{"status": "ok"}`` when the app is serving."""
    return {"status": "ok"}
