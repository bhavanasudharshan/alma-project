"""The single source of truth for lead state changes (E1).

Adding a state is one enum member plus one entry in ``TRANSITIONS`` -- no router,
service or repository changes. Each edge carries its own rules, so behaviour that
varies per transition (today: whether the prospect is told) lives with the edge
rather than in an ``if`` somewhere else.
"""

from dataclasses import dataclass

from app.db.models.lead import LeadState
from app.services.exceptions import AlreadyInState, InvalidTransition


@dataclass(frozen=True)
class TransitionRule:
    """What happens when a lead takes this edge.

    :param notify_prospect: whether the prospect should be emailed about the change.
        Declared now, wired up in a later stage (EXT2) -- the outbox pattern is the
        prerequisite for making that delivery reliable.
    """

    notify_prospect: bool = False


TRANSITIONS: dict[LeadState, dict[LeadState, TransitionRule]] = {
    LeadState.PENDING: {LeadState.REACHED_OUT: TransitionRule(notify_prospect=True)},
    LeadState.REACHED_OUT: {},
}


def rule_for(current: LeadState, new: LeadState) -> TransitionRule | None:
    """Return the rule for ``current -> new``, or ``None`` if the edge does not exist."""
    return TRANSITIONS.get(current, {}).get(new)


def assert_transition(current: LeadState, new: LeadState) -> None:
    """Raise unless ``current -> new`` is a legal edge.

    Two distinct failures, because the client should treat them differently:

    * :class:`AlreadyInState` -- the lead is *already* where the caller asked it to be.
      Benign; the UI reports it calmly and refreshes.
    * :class:`InvalidTransition` -- a move the pipeline does not allow at all.

    Both surface as HTTP 409, distinguished by their ``code``.
    """
    if current == new:
        raise AlreadyInState(f"This lead is already {new}.")
    if rule_for(current, new) is None:
        raise InvalidTransition(f"Cannot move a lead from {current} to {new}.")
