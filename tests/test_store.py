from datetime import UTC, datetime

import pytest

from kuzuryu_board_meetings.models import AttendanceRecord
from kuzuryu_board_meetings.store import BoardStore


def test_full_board_lifecycle() -> None:
    store = BoardStore()
    meeting = store.start_meeting("Test", "T1", "C1", "U1", "Alice Example (alice)")
    attendee = AttendanceRecord(
        user_id="U1",
        name="Alice Example (alice)",
        recorded_at=datetime.now(UTC),
    )

    store.update_quorum("T1", "C1", "set", [attendee], "U1")
    motion = store.create_motion(
        "T1",
        "C1",
        "Approve",
        ["Yes", "No"],
        "U1",
        "Alice Example (alice)",
    )
    store.cast_vote(motion.id, "U1", "Alice Example (alice)", "Yes")
    store.close_motion(motion.id)
    closed = store.close_active_meeting("T1", "C1")

    assert closed.id == meeting.id
    assert closed.status == "closed"
    assert closed.motions[0].votes[0].option == "Yes"


def test_invalid_vote_option_is_rejected() -> None:
    store = BoardStore()
    store.start_meeting("Test", "T1", "C1", None, None)
    motion = store.create_motion("T1", "C1", "Approve", ["Yes", "No"], None, None)

    with pytest.raises(ValueError, match="invalid vote option"):
        store.cast_vote(motion.id, "U1", None, "Maybe")
