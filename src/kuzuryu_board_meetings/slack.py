"""Slack request, profile, and command helpers."""

from __future__ import annotations

import hashlib
import hmac
import json
import shlex
import time
from datetime import UTC, datetime
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode
from urllib.request import Request, urlopen

from .models import AttendanceRecord


class SlackClient:
    def __init__(self, bot_token: str | None = None) -> None:
        self.bot_token = bot_token
        self.name_cache: dict[str, str] = {}

    def user_name(self, user_id: str | None, fallback: str | None = None) -> str | None:
        if not user_id:
            return clean_name(fallback)
        cached = self.name_cache.get(user_id)
        if cached:
            return cached
        name = self._lookup_user_name(user_id, fallback)
        return self._cache_user_name(user_id, name)

    def conversation_history(
        self,
        channel_id: str,
        oldest: str,
        latest: str | None = None,
    ) -> list[dict]:
        if not self.bot_token:
            return []
        query = {"channel": channel_id, "oldest": oldest, "limit": "200", "inclusive": "true"}
        if latest:
            query["latest"] = latest
        return self._paged_history(query)

    def message_user_name(self, message: dict) -> str | None:
        profile = message.get("user_profile")
        if isinstance(profile, dict):
            user = {
                "name": profile.get("name"),
                "real_name": profile.get("real_name"),
                "profile": profile,
            }
            name = profile_display_name(user, message.get("username"))
            if name and message.get("user"):
                self.name_cache[message["user"]] = name
            return name
        return self.user_name(message.get("user"), message.get("username"))

    def _paged_history(self, query: dict[str, str]) -> list[dict]:
        messages: list[dict] = []
        cursor = ""
        while True:
            body = self._history_page(query, cursor)
            messages.extend(body.messages)
            cursor = body.next_cursor
            if not cursor:
                return messages

    def _lookup_user_name(self, user_id: str, fallback: str | None) -> str | None:
        if not self.bot_token:
            return clean_name(fallback)
        body = self._get("https://slack.com/api/users.info", {"user": user_id})
        if not body.get("ok"):
            return clean_name(fallback)
        return profile_display_name(body.get("user") or {}, fallback)

    def _cache_user_name(self, user_id: str, name: str | None) -> str | None:
        if name:
            self.name_cache[user_id] = name
        return name

    def _history_page(self, query: dict[str, str], cursor: str) -> HistoryPage:
        page_query = {**query, **({"cursor": cursor} if cursor else {})}
        body = self._get("https://slack.com/api/conversations.history", page_query)
        return HistoryPage.from_response(body)

    def _get(self, url: str, query: dict[str, str]) -> dict:
        request = Request(
            f"{url}?{urlencode(query)}",
            headers={"Authorization": f"Bearer {self.bot_token}"},
        )
        try:
            with urlopen(request, timeout=5) as response:
                return json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, json.JSONDecodeError):
            return {"ok": False}


def clean_name(value: str | None) -> str | None:
    if not value:
        return None
    name = value.strip()
    return name or None


def profile_display_name(user: dict, fallback: str | None = None) -> str | None:
    profile = user.get("profile") or {}
    username = first_name(user.get("name"), profile.get("name"))
    primary = first_name(
        profile.get("real_name"),
        user.get("real_name"),
        profile.get("display_name"),
    )
    if should_append_username(primary, username):
        return f"{primary} ({username})"
    return primary or username or clean_name(fallback)


def first_name(*values: str | None) -> str | None:
    return next((name for value in values if (name := clean_name(value))), None)


def should_append_username(primary: str | None, username: str | None) -> bool:
    if not primary or not username:
        return False
    return primary.lower() != username.lower()


def verify_signature(
    secret: str | None,
    body: bytes,
    timestamp: str | None,
    signature: str | None,
) -> bool:
    if not secret:
        return True
    if not timestamp or not signature:
        return False
    if abs(time.time() - int(timestamp)) > 300:
        return False
    base = f"v0:{timestamp}:".encode() + body
    expected = "v0=" + hmac.new(secret.encode("utf-8"), base, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def parse_form(body: bytes) -> dict[str, str]:
    return {key: values[0] if values else "" for key, values in parse_qs(body.decode()).items()}


def split_command(text: str) -> tuple[str, list[str]]:
    try:
        tokens = shlex.split(text)
    except ValueError:
        tokens = text.split()
    return (tokens[0].lower(), tokens[1:]) if tokens else ("help", [])


def is_control_message(text: str) -> bool:
    command = text.strip().lower()
    return command.startswith("/board") or command.startswith("/vote")


def slack_ts(value: datetime) -> str:
    return str(value.timestamp())


def attendee_from_token(
    token: str,
    recorder_id: str | None,
    slack: SlackClient,
) -> AttendanceRecord:
    now = datetime.now(UTC)
    if token.startswith("<@") and token.endswith(">"):
        user_id, label = parse_mention(token)
        return AttendanceRecord(
            user_id=user_id,
            name=slack.user_name(user_id, label) or label or user_id,
            recorded_by=recorder_id,
            recorded_at=now,
        )
    return AttendanceRecord(name=token.lstrip("@"), recorded_by=recorder_id, recorded_at=now)


def parse_mention(token: str) -> tuple[str, str | None]:
    body = token.removeprefix("<@").removesuffix(">")
    if "|" not in body:
        return body, None
    user_id, label = body.split("|", 1)
    return user_id, label


class HistoryPage:
    def __init__(self, messages: list[dict], next_cursor: str) -> None:
        self.messages = messages
        self.next_cursor = next_cursor

    @classmethod
    def from_response(cls, body: dict) -> HistoryPage:
        if not body.get("ok"):
            return cls([], "")
        metadata = body.get("response_metadata") or {}
        return cls(body.get("messages") or [], (metadata.get("next_cursor") or "").strip())
