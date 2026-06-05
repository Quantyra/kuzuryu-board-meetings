from datetime import UTC, datetime

from kuzuryu_board_meetings.minutes import meeting_slug, render_minutes
from kuzuryu_board_meetings.models import AttendanceRecord, MeetingRecord, MotionRecord, VoteRecord


def test_render_minutes_includes_names_and_tally() -> None:
    meeting = MeetingRecord(
        id="bm-test",
        title="June Board",
        workspace_id="T1",
        channel_id="C1",
        chair_name="Daniel Eric Fredriksen (dfredriksen)",
        started_at=datetime(2026, 6, 5, tzinfo=UTC),
        attendance=[
            AttendanceRecord(
                user_id="U1",
                name="Daniel Eric Fredriksen (dfredriksen)",
                recorded_at=datetime(2026, 6, 5, tzinfo=UTC),
            )
        ],
        motions=[
            MotionRecord(
                id="mot-test",
                meeting_id="bm-test",
                text="Approve minutes",
                options=["Yes", "No", "Abstain"],
                created_at=datetime(2026, 6, 5, tzinfo=UTC),
                votes=[
                    VoteRecord(
                        voter_id="U1",
                        voter_name="Daniel Eric Fredriksen (dfredriksen)",
                        option="Yes",
                        cast_at=datetime(2026, 6, 5, tzinfo=UTC),
                    )
                ],
            )
        ],
    )

    rendered = render_minutes(meeting)

    assert "Chair: Daniel Eric Fredriksen (dfredriksen)" in rendered
    assert "- Daniel Eric Fredriksen (dfredriksen)" in rendered
    assert "Yes: 1" in rendered


def test_meeting_slug_is_filesystem_friendly() -> None:
    assert meeting_slug("Final Test(?)") == "final-test"

