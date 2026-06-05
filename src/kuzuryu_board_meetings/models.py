"""Pydantic models for board meetings."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class Person(BaseModel):
    user_id: str | None = None
    name: str


class AttendanceRecord(Person):
    present: bool = True
    recorded_by: str | None = None
    recorded_at: datetime


class CapturedMessage(BaseModel):
    user_id: str | None = None
    user_name: str | None = None
    text: str
    message_ts: str
    captured_at: datetime
    event_type: str = "message"


class VoteRecord(BaseModel):
    voter_id: str
    voter_name: str | None = None
    option: str
    cast_at: datetime


class MotionRecord(BaseModel):
    id: str
    meeting_id: str
    text: str
    options: list[str]
    status: str = "open"
    creator_id: str | None = None
    creator_name: str | None = None
    created_at: datetime
    closed_at: datetime | None = None
    votes: list[VoteRecord] = Field(default_factory=list)


class MeetingRecord(BaseModel):
    id: str
    title: str
    workspace_id: str
    channel_id: str
    status: str = "open"
    chair_id: str | None = None
    chair_name: str | None = None
    started_at: datetime
    closed_at: datetime | None = None
    messages: list[CapturedMessage] = Field(default_factory=list)
    attendance: list[AttendanceRecord] = Field(default_factory=list)
    motions: list[MotionRecord] = Field(default_factory=list)


class MinutesResponse(BaseModel):
    meeting: MeetingRecord
    markdown: str
    published_path: str | None = None
    published_commit: str | None = None
    publish_error: str | None = None

