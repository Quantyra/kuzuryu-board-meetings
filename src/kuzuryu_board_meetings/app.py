"""FastAPI application for Kuzuryu Board Meetings."""

from __future__ import annotations

from fastapi import Depends, FastAPI, Header, HTTPException, Request

from .config import Settings, load_settings
from .minutes import render_minutes, vote_tally
from .models import AttendanceRecord, MinutesResponse
from .publisher import publish_minutes
from .slack import (
    SlackClient,
    attendee_from_token,
    is_control_message,
    parse_form,
    slack_ts,
    split_command,
    verify_signature,
)
from .store import BoardStore


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or load_settings()
    store = BoardStore()
    slack = SlackClient(app_settings.slack_bot_token)
    app = FastAPI(title="Kuzuryu Board Meetings", version="0.1.0")

    def require_auth(x_board_token: str | None = Header(default=None)) -> None:
        if app_settings.board_auth_token and x_board_token != app_settings.board_auth_token:
            raise HTTPException(status_code=401, detail="Invalid board token")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/board/meetings", dependencies=[Depends(require_auth)])
    def start_meeting(payload: dict) -> dict:
        meeting = store.start_meeting(
            payload["title"],
            payload["workspace_id"],
            payload["channel_id"],
            payload.get("chair_id"),
            payload.get("chair_name"),
        )
        return meeting.model_dump(mode="json")

    @app.post("/board/messages", dependencies=[Depends(require_auth)])
    def capture_message(payload: dict) -> dict:
        meeting = store.capture_message(
            payload["workspace_id"],
            payload["channel_id"],
            payload.get("user_id"),
            payload.get("user_name"),
            payload["text"],
            payload["message_ts"],
            payload.get("event_type", "message"),
        )
        return meeting.model_dump(mode="json")

    @app.post("/board/meetings/active/quorum", dependencies=[Depends(require_auth)])
    def update_quorum(payload: dict) -> dict:
        attendees = [AttendanceRecord(**item) for item in payload.get("attendees", [])]
        meeting = store.update_quorum(
            payload["workspace_id"],
            payload["channel_id"],
            payload.get("action", "set"),
            attendees,
            payload.get("recorder_id"),
        )
        return meeting.model_dump(mode="json")

    @app.post("/board/motions", dependencies=[Depends(require_auth)])
    def create_motion(payload: dict) -> dict:
        motion = store.create_motion(
            payload["workspace_id"],
            payload["channel_id"],
            payload["text"],
            payload.get("options") or ["Yes", "No", "Abstain"],
            payload.get("creator_id"),
            payload.get("creator_name"),
        )
        return motion.model_dump(mode="json")

    @app.post("/board/motions/{motion_id}/votes", dependencies=[Depends(require_auth)])
    def cast_vote(motion_id: str, payload: dict) -> dict:
        motion = store.cast_vote(
            motion_id,
            payload["voter_id"],
            payload.get("voter_name"),
            payload["option"],
        )
        return motion.model_dump(mode="json")

    @app.post("/board/motions/{motion_id}/close", dependencies=[Depends(require_auth)])
    def close_motion(motion_id: str) -> dict:
        return store.close_motion(motion_id).model_dump(mode="json")

    @app.post("/board/meetings/active/close", dependencies=[Depends(require_auth)])
    def close_meeting(payload: dict) -> MinutesResponse:
        backfill_history(store, slack, payload["workspace_id"], payload["channel_id"])
        meeting = store.close_active_meeting(payload["workspace_id"], payload["channel_id"])
        markdown = render_minutes(meeting)
        path, commit, error = publish_minutes(app_settings, meeting, markdown)
        return MinutesResponse(
            meeting=meeting,
            markdown=markdown,
            published_path=path,
            published_commit=commit,
            publish_error=error,
        )

    @app.get("/board/meetings/{meeting_id}/minutes", dependencies=[Depends(require_auth)])
    def get_minutes(meeting_id: str) -> MinutesResponse:
        meeting = store.meetings[meeting_id]
        return MinutesResponse(meeting=meeting, markdown=render_minutes(meeting))

    @app.post("/commands")
    async def slack_command(
        request: Request,
        x_slack_signature: str | None = Header(default=None),
        x_slack_request_timestamp: str | None = Header(default=None),
    ) -> dict:
        body = await request.body()
        verified = verify_signature(
            app_settings.slack_signing_secret,
            body,
            x_slack_request_timestamp,
            x_slack_signature,
        )
        if not verified:
            raise HTTPException(status_code=401, detail="Invalid Slack signature")
        return dispatch_slack_command(store, slack, parse_form(body))

    @app.post("/events")
    async def slack_event(request: Request) -> dict:
        payload = await request.json()
        if payload.get("type") == "url_verification":
            return {"challenge": payload.get("challenge")}
        capture_event_message(store, slack, payload)
        return {"ok": True}

    return app


def dispatch_slack_command(store: BoardStore, slack: SlackClient, form: dict[str, str]) -> dict:
    command, args = split_command(form.get("text", ""))
    if form.get("command") == "/vote":
        return dispatch_vote(store, slack, form, command, args)
    return dispatch_board(store, slack, form, command, args)


def dispatch_board(
    store: BoardStore,
    slack: SlackClient,
    form: dict[str, str],
    command: str,
    args: list[str],
) -> dict:
    workspace_id = form.get("team_id") or form.get("team_domain") or "unknown-workspace"
    channel_id = form.get("channel_id", "")
    user_id = form.get("user_id")
    context = BoardContext(store, slack, workspace_id, channel_id, user_id, form.get("user_name"))
    handler = BOARD_HANDLERS.get(command)
    return handler(context, args) if handler else slack_error(BOARD_USAGE)


class BoardContext:
    def __init__(
        self,
        store: BoardStore,
        slack: SlackClient,
        workspace_id: str,
        channel_id: str,
        user_id: str | None,
        user_name: str | None,
    ) -> None:
        self.store = store
        self.slack = slack
        self.workspace_id = workspace_id
        self.channel_id = channel_id
        self.user_id = user_id
        self.user_name = user_name


def start_board(context: BoardContext, args: list[str]) -> dict:
    title = " ".join(args).strip() or "Board Meeting"
    meeting = context.store.start_meeting(
        title,
        context.workspace_id,
        context.channel_id,
        context.user_id,
        context.slack.user_name(context.user_id, context.user_name),
    )
    return slack_success(f"Board meeting started: {meeting.title} (`{meeting.id}`).")


def quorum_board(context: BoardContext, args: list[str]) -> dict:
    return handle_quorum(
        context.store,
        context.slack,
        context.workspace_id,
        context.channel_id,
        context.user_id,
        args,
    )


def close_board(context: BoardContext, _args: list[str]) -> dict:
    backfill_history(context.store, context.slack, context.workspace_id, context.channel_id)
    meeting = context.store.close_active_meeting(context.workspace_id, context.channel_id)
    return slack_success(close_message(meeting.id, render_minutes(meeting)))


def handle_quorum(
    store: BoardStore,
    slack: SlackClient,
    workspace_id: str,
    channel_id: str,
    user_id: str | None,
    args: list[str],
) -> dict:
    action = quorum_action(args)
    tokens = args[1:] if action != "set" else args
    attendees = [attendee_from_token(token, user_id, slack) for token in tokens]
    meeting = store.update_quorum(workspace_id, channel_id, action, attendees, user_id)
    lines = quorum_lines(meeting.attendance)
    return slack_success(f"Quorum recorded for `{meeting.id}`:\n" + "\n".join(lines))


def dispatch_vote(
    store: BoardStore,
    slack: SlackClient,
    form: dict[str, str],
    command: str,
    args: list[str],
) -> dict:
    handler = VOTE_HANDLERS.get(command)
    if not handler or not args:
        return slack_error(VOTE_USAGE)
    return handler(vote_context(store, slack, form), args)


def backfill_history(
    store: BoardStore,
    slack: SlackClient,
    workspace_id: str,
    channel_id: str,
) -> None:
    meeting = store.active_meeting(workspace_id, channel_id)
    for message in slack.conversation_history(
        channel_id,
        slack_ts(meeting.started_at),
        slack_ts_now(),
    ):
        if should_capture_history_message(message):
            capture_history_message(store, slack, workspace_id, channel_id, message)


def capture_event_message(store: BoardStore, slack: SlackClient, payload: dict) -> None:
    event = payload.get("event") or {}
    if not should_capture_event(event):
        return
    store.capture_message(
        payload.get("team_id") or event.get("team") or "unknown-workspace",
        event["channel"],
        event.get("user"),
        slack.user_name(event.get("user"), event.get("username")),
        event["text"],
        event["ts"],
    )


def should_capture_history_message(message: dict) -> bool:
    text = str(message.get("text") or "")
    return bool(text.strip() and not message.get("subtype") and not is_control_message(text))


def capture_history_message(
    store: BoardStore,
    slack: SlackClient,
    workspace_id: str,
    channel_id: str,
    message: dict,
) -> None:
    store.capture_message(
        workspace_id,
        channel_id,
        message.get("user"),
        slack.message_user_name(message),
        str(message.get("text") or ""),
        message.get("ts", ""),
        "history",
    )


def should_capture_event(event: dict) -> bool:
    return bool(event.get("type") == "message" and not event.get("subtype") and event.get("text"))


def slack_ts_now() -> str:
    from time import time

    return str(time())


def slack_success(text: str) -> dict[str, str]:
    return {"response_type": "in_channel", "text": text}


def slack_error(text: str) -> dict[str, str]:
    return {"response_type": "ephemeral", "text": text}


def close_message(meeting_id: str, markdown: str) -> str:
    return f"Board meeting closed: `{meeting_id}`. Draft minutes:\n```{markdown[:2500]}```"


def quorum_action(args: list[str]) -> str:
    if args and args[0].lower() in {"set", "add", "remove", "list"}:
        return args[0].lower()
    return "set"


def quorum_lines(attendance: list[AttendanceRecord]) -> list[str]:
    return [f"- {item.name}" for item in attendance if item.present] or ["No attendees recorded."]


class VoteContext:
    def __init__(
        self,
        store: BoardStore,
        workspace_id: str,
        channel_id: str,
        user_id: str,
        user_name: str | None,
    ) -> None:
        self.store = store
        self.workspace_id = workspace_id
        self.channel_id = channel_id
        self.user_id = user_id
        self.user_name = user_name


def vote_context(store: BoardStore, slack: SlackClient, form: dict[str, str]) -> VoteContext:
    user_id = form.get("user_id") or ""
    return VoteContext(
        store,
        workspace_id(form),
        form.get("channel_id", ""),
        user_id,
        slack.user_name(user_id, form.get("user_name")),
    )


def workspace_id(form: dict[str, str]) -> str:
    return form.get("team_id") or form.get("team_domain") or "unknown-workspace"


def create_vote(context: VoteContext, args: list[str]) -> dict:
    motion = context.store.create_motion(
        context.workspace_id,
        context.channel_id,
        args[0],
        args[1:] or ["Yes", "No", "Abstain"],
        context.user_id,
        context.user_name,
    )
    return slack_success(f"Vote created `{motion.id}`: {motion.text}")


def cast_vote_command(context: VoteContext, args: list[str]) -> dict:
    motion = context.store.cast_vote(
        args[0],
        context.user_id,
        context.user_name,
        " ".join(args[1:]),
    )
    return vote_recorded_response(
        motion.id,
        context.user_name or context.user_id,
        motion.votes[-1].option,
    )


def recuse_vote(context: VoteContext, args: list[str]) -> dict:
    motion = context.store.cast_vote(args[0], context.user_id, context.user_name, "Recused")
    return vote_recorded_response(
        motion.id,
        context.user_name or context.user_id,
        motion.votes[-1].option,
    )


def close_vote(context: VoteContext, args: list[str]) -> dict:
    motion = context.store.close_motion(args[0])
    tally = ", ".join(f"{option}: {count}" for option, count in vote_tally(motion).items())
    return slack_success(f"Vote closed `{motion.id}`. Tally: {tally}.")


def vote_recorded_response(motion_id: str, name: str, option: str) -> dict:
    return slack_success(f"Vote recorded for `{motion_id}`: {name} = {option}.")


VOTE_USAGE = (
    'Usage: `/vote create "Motion text"`, `/vote cast <motion-id> <option>`, '
    "or `/vote close <motion-id>`."
)
VOTE_HANDLERS = {
    "create": create_vote,
    "cast": cast_vote_command,
    "recuse": recuse_vote,
    "close": close_vote,
}
BOARD_USAGE = (
    'Usage: `/board start "Meeting title"`, `/board quorum @Alice @Bob`, '
    "or `/board close`."
)
BOARD_HANDLERS = {
    "start": start_board,
    "quorum": quorum_board,
    "close": close_board,
}


def main() -> None:
    import uvicorn

    uvicorn.run(create_app(), host="0.0.0.0", port=8000)
