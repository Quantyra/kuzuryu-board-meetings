"""Runtime configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    board_auth_token: str | None = os.getenv("BOARD_AUTH_TOKEN")
    slack_signing_secret: str | None = os.getenv("SLACK_SIGNING_SECRET")
    slack_bot_token: str | None = os.getenv("SLACK_BOT_TOKEN")
    minutes_git_url: str | None = os.getenv("MINUTES_GIT_URL")
    minutes_git_branch: str = os.getenv("MINUTES_GIT_BRANCH", "main")
    minutes_git_path: str = os.getenv("MINUTES_GIT_PATH", "board-minutes")
    minutes_git_dir: Path = Path(os.getenv("MINUTES_GIT_DIR", "./board-minutes-repo"))
    minutes_git_author_name: str = os.getenv(
        "MINUTES_GIT_AUTHOR_NAME", "Kuzuryu Board Meetings"
    )
    minutes_git_author_email: str = os.getenv(
        "MINUTES_GIT_AUTHOR_EMAIL", "board-meetings@example.invalid"
    )
    minutes_git_ssh_key: str | None = os.getenv("MINUTES_GIT_SSH_KEY")
    board_state_path: Path | None = (
        Path(path) if (path := os.getenv("BOARD_STATE_PATH")) else None
    )


def load_settings() -> Settings:
    return Settings()
