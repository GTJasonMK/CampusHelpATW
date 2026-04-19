TASK_TRANSITIONS: dict[str, set[str]] = {
    "OPEN": {"ACCEPTED", "CANCELED"},
    "ACCEPTED": {"IN_PROGRESS", "CANCELED"},
    "IN_PROGRESS": {"PENDING_CONFIRM", "CANCELED", "DISPUTED"},
    "PENDING_CONFIRM": {"DONE", "DISPUTED"},
    "DISPUTED": {"DONE", "CANCELED"},
    "DONE": set(),
    "CANCELED": set(),
}


def can_transition(from_status: str, to_status: str) -> bool:
    return to_status in TASK_TRANSITIONS.get(from_status, set())


def ensure_transition(from_status: str, to_status: str) -> None:
    if not can_transition(from_status, to_status):
        raise ValueError(f"invalid task status transition: {from_status} -> {to_status}")

