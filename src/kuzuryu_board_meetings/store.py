"""In-memory board meeting store."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from .models import AttendanceRecord, CapturedMessage, MeetingRecord, MotionRecord, VoteRecord

RECUSE_OPTIONS = {"recuse": "Recused", "recused": "Recused"}


class BoardStore:
    def __init__(self) -> None:
        self.meetings: dict[str, MeetingRecord] = {}
        self.active_by_channel: dict[tuple[str, str], str] = {}
        self.motions: dict[str, MotionRecord] = {}

    def start_meeting(
        self,
        title: str,
        workspace_id: str,
        channel_id: str,
        chair_id: str | None,
        chair_name: str | None,
    ) -> MeetingRecord:
        key = (workspace_id, channel_id)
        if key in self.active_by_channel:
            raise ValueError("meeting already active")
        meeting = MeetingRecord(
            id=f"bm-{uuid4().hex[:8]}",
            title=title.strip() or "Board Meeting",
            workspace_id=workspace_id,
            channel_id=channel_id,
            chair_id=chair_id,
            chair_name=chair_name,
            started_at=datetime.now(UTC),
        )
        self.meetings[meeting.id] = meeting
        self.active_by_channel[key] = meeting.id
        return meeting

    def active_meeting(self, workspace_id: str, channel_id: str) -> MeetingRecord:
        meeting_id = self.active_by_channel.get((workspace_id, channel_id))
        if not meeting_id:
            raise KeyError("active meeting not found")
        return self.meetings[meeting_id]

    def capture_message(
        self,
        workspace_id: str,
        channel_id: str,
        user_id: str | None,
        user_name: str | None,
        text: str,
        message_ts: str,
        event_type: str = "message",
    ) -> MeetingRecord:
        meeting = self.active_meeting(workspace_id, channel_id)
        if not text.strip() or has_message(meeting, message_ts):
            return meeting
        meeting.messages.append(
            CapturedMessage(
                user_id=user_id,
                user_name=user_name,
                text=text.strip(),
                message_ts=message_ts,
                captured_at=datetime.now(UTC),
                event_type=event_type,
            )
        )
        return meeting

    def update_quorum(
        self,
        workspace_id: str,
        channel_id: str,
        action: str,
        attendees: list[AttendanceRecord],
        recorder_id: str | None,
    ) -> MeetingRecord:
        meeting = self.active_meeting(workspace_id, channel_id)
        if action == "list":
            return meeting
        incoming = [
            item.model_copy(update={"recorded_by": item.recorded_by or recorder_id})
            for item in attendees
        ]
        meeting.attendance = quorum_after_action(meeting.attendance, incoming, action)
        return meeting

    def create_motion(
        self,
        workspace_id: str,
        channel_id: str,
        text: str,
        options: list[str],
        creator_id: str | None,
        creator_name: str | None,
    ) -> MotionRecord:
        meeting = self.active_meeting(workspace_id, channel_id)
        cleaned_options = [option.strip() for option in options if option.strip()]
        if len(cleaned_options) < 2:
            raise ValueError("at least two options required")
        motion = MotionRecord(
            id=f"mot-{uuid4().hex[:8]}",
            meeting_id=meeting.id,
            text=text.strip(),
            options=cleaned_options,
            creator_id=creator_id,
            creator_name=creator_name,
            created_at=datetime.now(UTC),
        )
        if not motion.text:
            raise ValueError("motion text required")
        meeting.motions.append(motion)
        self.motions[motion.id] = motion
        return motion

    def cast_vote(
        self,
        motion_id: str,
        voter_id: str,
        voter_name: str | None,
        option: str,
    ) -> MotionRecord:
        motion = self._open_motion(motion_id)
        vote_option = normalized_vote_option(motion.options, option)
        motion.votes = [vote for vote in motion.votes if vote.voter_id != voter_id]
        motion.votes.append(
            VoteRecord(
                voter_id=voter_id,
                voter_name=voter_name,
                option=vote_option,
                cast_at=datetime.now(UTC),
            )
        )
        return motion

    def close_motion(self, motion_id: str) -> MotionRecord:
        motion = self.motions[motion_id]
        motion.status = "closed"
        motion.closed_at = datetime.now(UTC)
        return motion

    def close_active_meeting(self, workspace_id: str, channel_id: str) -> MeetingRecord:
        meeting = self.active_meeting(workspace_id, channel_id)
        meeting.status = "closed"
        meeting.closed_at = datetime.now(UTC)
        self.active_by_channel.pop((workspace_id, channel_id), None)
        return meeting

    def _open_motion(self, motion_id: str) -> MotionRecord:
        motion = self.motions[motion_id]
        if motion.status != "open":
            raise ValueError("motion is closed")
        return motion


def attendance_key(attendee: AttendanceRecord) -> str:
    return attendee.user_id or attendee.name.strip().lower()


def has_message(meeting: MeetingRecord, message_ts: str) -> bool:
    return any(message.message_ts == message_ts for message in meeting.messages)


def quorum_after_action(
    current: list[AttendanceRecord], incoming: list[AttendanceRecord], action: str
) -> list[AttendanceRecord]:
    handlers = {
        "set": replace_quorum,
        "add": add_quorum,
        "remove": remove_quorum,
    }
    if action not in handlers:
        raise ValueError("quorum action must be set, add, remove, or list")
    return handlers[action](current, incoming)


def replace_quorum(
    _current: list[AttendanceRecord],
    incoming: list[AttendanceRecord],
) -> list[AttendanceRecord]:
    return incoming


def add_quorum(
    current: list[AttendanceRecord],
    incoming: list[AttendanceRecord],
) -> list[AttendanceRecord]:
    attendees = {attendance_key(item): item for item in current}
    attendees.update({attendance_key(item): item for item in incoming})
    return list(attendees.values())


def remove_quorum(
    current: list[AttendanceRecord],
    incoming: list[AttendanceRecord],
) -> list[AttendanceRecord]:
    remove_keys = {attendance_key(item) for item in incoming}
    return [item for item in current if attendance_key(item) not in remove_keys]


def normalized_vote_option(options: list[str], option: str) -> str:
    requested = option.strip().lower()
    matching_options = {item.lower(): item for item in options}
    vote_option = matching_options.get(requested) or RECUSE_OPTIONS.get(requested)
    if not vote_option:
        raise ValueError("invalid vote option")
    return vote_option
