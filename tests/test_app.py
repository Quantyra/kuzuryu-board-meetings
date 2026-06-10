
from fastapi.testclient import TestClient

from kuzuryu_board_meetings.app import create_app
from kuzuryu_board_meetings.config import Settings


def test_api_board_flow_without_slack() -> None:
    client = TestClient(create_app(Settings(board_auth_token="token")))
    headers = {"X-Board-Token": "token"}

    start = client.post(
        "/board/meetings",
        json={"title": "Test", "workspace_id": "T1", "channel_id": "C1", "chair_name": "Chair"},
        headers=headers,
    )
    assert start.status_code == 200
    motion = client.post(
        "/board/motions",
        json={
            "workspace_id": "T1",
            "channel_id": "C1",
            "text": "Approve",
            "options": ["Yes", "No"],
        },
        headers=headers,
    ).json()
    client.post(
        f"/board/motions/{motion['id']}/votes",
        json={"voter_id": "U1", "voter_name": "Alice Example (alice)", "option": "Yes"},
        headers=headers,
    )
    closed = client.post(
        "/board/meetings/active/close",
        json={"workspace_id": "T1", "channel_id": "C1"},
        headers=headers,
    )

    assert closed.status_code == 200
    assert "Alice Example (alice): Yes" in closed.json()["markdown"]


def test_slack_command_flow() -> None:
    client = TestClient(create_app())
    start = client.post(
        "/commands",
        data={
            "command": "/board",
            "text": "start Local Meeting",
            "team_id": "T1",
            "channel_id": "C1",
            "user_id": "U1",
            "user_name": "alice",
        },
    )

    assert start.status_code == 200
    assert "Board meeting started" in start.json()["text"]


def test_active_meeting_survives_app_restart(tmp_path) -> None:
    settings = Settings(board_auth_token="token", board_state_path=tmp_path / "board-state.json")
    headers = {"X-Board-Token": "token"}
    client = TestClient(create_app(settings))
    start = client.post(
        "/board/meetings",
        json={"title": "Restart Test", "workspace_id": "T1", "channel_id": "C1"},
        headers=headers,
    )
    assert start.status_code == 200

    restarted = TestClient(create_app(settings))
    closed = restarted.post(
        "/board/meetings/active/close",
        json={"workspace_id": "T1", "channel_id": "C1"},
        headers=headers,
    )

    assert closed.status_code == 200
    assert closed.json()["meeting"]["id"] == start.json()["id"]
    assert closed.json()["meeting"]["status"] == "closed"


def test_slack_event_url_verification() -> None:
    client = TestClient(create_app())
    response = client.post("/events", json={"type": "url_verification", "challenge": "abc"})

    assert response.json() == {"challenge": "abc"}


def test_history_backfill_uses_profile_and_filters_commands(monkeypatch) -> None:
    app = create_app()
    client = TestClient(app)
    client.post(
        "/commands",
        data={
            "command": "/board",
            "text": "start History",
            "team_id": "T1",
            "channel_id": "C1",
            "user_id": "U1",
            "user_name": "alice",
        },
    )

    def fake_history(channel_id: str, oldest: str, latest: str | None = None) -> list[dict]:
        return [
            {"text": "/board quorum @Alice", "ts": "1", "user": "U1"},
            {
                "text": "Actual discussion",
                "ts": "2",
                "user": "U1",
                "user_profile": {"real_name": "Alice Example", "name": "alice"},
            },
        ]

    slack = _find_slack_client(app)
    monkeypatch.setattr(slack, "conversation_history", fake_history)
    response = client.post(
        "/commands",
        data={"command": "/board", "text": "close", "team_id": "T1", "channel_id": "C1"},
    )

    text = response.json()["text"]
    assert "Alice Example (alice): Actual discussion" in text
    assert "/board quorum" not in text


def _find_slack_client(app):
    for cell in app.router.routes[-1].endpoint.__closure__ or []:
        value = cell.cell_contents
        if hasattr(value, "conversation_history"):
            return value
    raise AssertionError("Slack client not found")
