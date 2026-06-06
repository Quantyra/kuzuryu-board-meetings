import subprocess
from datetime import UTC, datetime
from pathlib import Path

from kuzuryu_board_meetings.config import Settings
from kuzuryu_board_meetings.models import MeetingRecord, Person
from kuzuryu_board_meetings.publisher import minutes_path, publish_minutes, run_git


def test_minutes_path_uses_utc_date_and_slug(tmp_path: Path) -> None:
    settings = Settings(minutes_git_path="records")
    meeting = MeetingRecord(
        id="bm-123",
        title="Annual Board Meeting",
        workspace_id="T1",
        channel_id="C1",
        chair=Person(name="Chair"),
        started_at=datetime(2026, 6, 6, 1, 2, tzinfo=UTC),
    )

    expected = Path("records/2026-06-06/annual-board-meeting-bm-123.md")

    assert minutes_path(settings, meeting) == expected


def test_publish_minutes_returns_none_when_disabled() -> None:
    meeting = MeetingRecord(
        id="bm-123",
        title="Disabled",
        workspace_id="T1",
        channel_id="C1",
        chair=Person(name="Chair"),
        started_at=datetime(2026, 6, 6, tzinfo=UTC),
    )

    assert publish_minutes(Settings(), meeting, "# Minutes") == (None, None, None)


def test_publish_minutes_commits_to_git_repo(tmp_path: Path) -> None:
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", str(remote)], check=True)
    seed = tmp_path / "seed"
    subprocess.run(["git", "clone", str(remote), str(seed)], check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=seed, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=seed, check=True)
    (seed / "README.md").write_text("seed\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=seed, check=True)
    subprocess.run(["git", "commit", "-m", "seed"], cwd=seed, check=True)
    subprocess.run(["git", "push", "origin", "master:main"], cwd=seed, check=True)

    settings = Settings(
        minutes_git_url=str(remote),
        minutes_git_branch="main",
        minutes_git_dir=tmp_path / "minutes-repo",
        minutes_git_path="board-minutes",
        minutes_git_author_name="Bot",
        minutes_git_author_email="bot@example.invalid",
    )
    meeting = MeetingRecord(
        id="bm-123",
        title="Publish Test",
        workspace_id="T1",
        channel_id="C1",
        chair=Person(name="Chair"),
        started_at=datetime(2026, 6, 6, tzinfo=UTC),
    )

    relative, commit, error = publish_minutes(settings, meeting, "# Minutes")

    assert error is None
    assert relative == "board-minutes/2026-06-06/publish-test-bm-123.md"
    assert commit
    assert (settings.minutes_git_dir / relative).read_text(encoding="utf-8") == "# Minutes\n"


def test_run_git_sets_ssh_command_when_key_configured(tmp_path: Path, monkeypatch) -> None:
    calls = []

    def fake_run(*args, **kwargs):
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(args[0], 0, stdout="ok\n", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    settings = Settings(minutes_git_ssh_key=tmp_path / "deploy_key")

    result = run_git(settings, ["status"], tmp_path)

    assert result.stdout == "ok\n"
    assert "GIT_SSH_COMMAND" in calls[0][1]["env"]
    assert str(settings.minutes_git_ssh_key) in calls[0][1]["env"]["GIT_SSH_COMMAND"]
