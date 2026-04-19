from app.domain.task_state_machine import TASK_TRANSITIONS, can_transition, ensure_transition


def test_task_transitions_has_all_core_statuses() -> None:
    for status in ["OPEN", "ACCEPTED", "IN_PROGRESS", "PENDING_CONFIRM", "DONE", "CANCELED", "DISPUTED"]:
        assert status in TASK_TRANSITIONS


def test_valid_transition_open_to_accepted() -> None:
    assert can_transition("OPEN", "ACCEPTED") is True


def test_invalid_transition_open_to_done() -> None:
    assert can_transition("OPEN", "DONE") is False


def test_ensure_transition_raises_for_invalid_path() -> None:
    try:
        ensure_transition("ACCEPTED", "DONE")
    except ValueError as exc:
        assert "invalid task status transition" in str(exc)
    else:
        raise AssertionError("expected ValueError not raised")

