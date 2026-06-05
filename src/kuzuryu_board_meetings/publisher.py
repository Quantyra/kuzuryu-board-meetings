"""Optional git publishing for board minutes."""

from __future__ import annotations

import os
import subprocess
from datetime import UTC
from pathlib import Path

from .config import Settings
from .minutes import meeting_slug
from .models import MeetingRecord


def publish_minutes(
    settings: Settings,
    meeting: MeetingRecord,
    markdown: str,
) -> tuple[str | None, str | None, str | None]:
    if not settings.minutes_git_url:
        return None, None, None
    try:
        repo = ensure_repo(settings)
        relative = minutes_path(settings, meeting)
        output = repo / relative
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(markdown + "\n", encoding="utf-8")
        commit = commit_and_push(settings, repo, relative, meeting.id)
        return str(relative).replace("\\", "/"), commit, None
    except Exception as exc:
        return None, None, f"git publish failed: {exc}"


def ensure_repo(settings: Settings) -> Path:
    repo = settings.minutes_git_dir
    if not (repo / ".git").exists():
        repo.parent.mkdir(parents=True, exist_ok=True)
        run_git(
            settings,
            ["clone", "--branch", settings.minutes_git_branch, settings.minutes_git_url, str(repo)],
        )
        return repo
    run_git(settings, ["fetch", "origin", settings.minutes_git_branch], repo)
    run_git(settings, ["checkout", settings.minutes_git_branch], repo)
    run_git(settings, ["pull", "--ff-only", "origin", settings.minutes_git_branch], repo)
    return repo


def minutes_path(settings: Settings, meeting: MeetingRecord) -> Path:
    day = meeting.started_at.astimezone(UTC).strftime("%Y-%m-%d")
    return Path(settings.minutes_git_path) / day / f"{meeting_slug(meeting.title)}-{meeting.id}.md"


def commit_and_push(settings: Settings, repo: Path, relative: Path, meeting_id: str) -> str:
    path = str(relative).replace("\\", "/")
    run_git(settings, ["config", "user.name", settings.minutes_git_author_name], repo)
    run_git(settings, ["config", "user.email", settings.minutes_git_author_email], repo)
    run_git(settings, ["add", path], repo)
    status = run_git(settings, ["status", "--porcelain", "--", path], repo).stdout.strip()
    if status:
        run_git(settings, ["commit", "-m", f"Add board minutes {meeting_id}"], repo)
        run_git(settings, ["push", "origin", settings.minutes_git_branch], repo)
    return run_git(settings, ["rev-parse", "HEAD"], repo).stdout.strip()


def run_git(
    settings: Settings,
    args: list[str],
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    if settings.minutes_git_ssh_key:
        env["GIT_SSH_COMMAND"] = (
            f"ssh -i {settings.minutes_git_ssh_key} "
            "-o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"
        )
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
