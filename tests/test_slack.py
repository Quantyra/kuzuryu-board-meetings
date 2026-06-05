from datetime import UTC, datetime

from kuzuryu_board_meetings.slack import (
    attendee_from_token,
    is_control_message,
    profile_display_name,
    slack_ts,
)


class FakeSlack:
    def user_name(self, user_id: str | None, fallback: str | None = None) -> str | None:
        return {"U1": "Alice Example (alice)"}.get(user_id or "", fallback)


def test_profile_display_name_prefers_full_name_with_username() -> None:
    user = {"name": "dfredriksen", "profile": {"real_name": "Daniel Eric Fredriksen"}}

    assert profile_display_name(user) == "Daniel Eric Fredriksen (dfredriksen)"


def test_attendee_from_slack_mention_resolves_name() -> None:
    attendee = attendee_from_token("<@U1|alice>", "U-chair", FakeSlack())

    assert attendee.user_id == "U1"
    assert attendee.name == "Alice Example (alice)"


def test_control_message_filter() -> None:
    assert is_control_message("/vote close mot-123")
    assert not is_control_message("Discussion text")


def test_slack_ts_uses_epoch_seconds() -> None:
    assert slack_ts(datetime(1970, 1, 1, tzinfo=UTC)) == "0.0"

