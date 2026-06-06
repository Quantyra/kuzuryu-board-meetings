import hashlib
import hmac
import time
from datetime import UTC, datetime

from kuzuryu_board_meetings.slack import (
    HistoryPage,
    attendee_from_token,
    clean_name,
    is_control_message,
    parse_form,
    profile_display_name,
    slack_ts,
    split_command,
    verify_signature,
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


def test_clean_name_and_split_command_handle_empty_and_quotes() -> None:
    assert clean_name("  Alice  ") == "Alice"
    assert clean_name("  ") is None
    assert split_command('create "Approve budget"') == ("create", ["Approve budget"])
    assert split_command('"unterminated') == ('"unterminated', [])


def test_parse_form_returns_first_value() -> None:
    assert parse_form(b"text=hello&text=ignored&empty=") == {"text": "hello"}


def test_verify_signature() -> None:
    secret = "secret"
    body = b"text=hello"
    timestamp = str(int(time.time()))
    base = f"v0:{timestamp}:".encode() + body
    signature = "v0=" + hmac.new(secret.encode(), base, hashlib.sha256).hexdigest()

    assert verify_signature(secret, body, timestamp, signature)
    assert not verify_signature(secret, body, timestamp, "v0=bad")
    assert not verify_signature(secret, body, str(int(time.time()) - 1000), signature)
    assert verify_signature(None, body, None, None)


def test_history_page_handles_failed_and_cursor_response() -> None:
    assert HistoryPage.from_response({"ok": False}).messages == []
    page = HistoryPage.from_response(
        {"ok": True, "messages": [{"text": "hello"}], "response_metadata": {"next_cursor": " abc "}}
    )

    assert page.messages == [{"text": "hello"}]
    assert page.next_cursor == "abc"
