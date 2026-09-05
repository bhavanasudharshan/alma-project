"""The single source of truth for lead state changes (E1).

Adding a state is one enum member plus one entry in ``TRANSITIONS`` -- no router,
service or repository changes.
"""

from app.db.models.lead import LeadState
from app.services.exceptions import InvalidTransition

TRANSITIONS: dict[LeadState, set[LeadState]] = {
    LeadState.PENDING: {LeadState.REACHED_OUT},
    LeadState.REACHED_OUT: set(),
}


def assert_transition(current: LeadState, new: LeadState) -> None:
    """Raise :class:`InvalidTransition` unless ``current -> new`` is allowed.

    Re-applying the current state is itself illegal, which makes ``PATCH`` safe to
    retry loudly rather than silently: the second call gets a 409 (R2/FR9).
    """
    if new not in TRANSITIONS.get(current, set()):
        raise InvalidTransition(f"Cannot move a lead from {current} to {new}.")
