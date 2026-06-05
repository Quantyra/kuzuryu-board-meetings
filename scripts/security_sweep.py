"""Fail if likely secrets are present in repository files."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".ruff_cache"}
EXCLUDED_FILES = {".coverage"}
EXCLUDED_SUFFIXES = {".pyc", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".zip", ".gz"}
SECRET_PATTERNS = [
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{20,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{30,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----"),
    re.compile(
        r"(?im)^(?:[^#\n]*)(client_secret|signing_secret|bot_token)"
        r"[ \t]*[:=][ \t]*[A-Za-z0-9/_+=.-]{16,}"
    ),
]


def iter_files() -> list[Path]:
    files = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.name in EXCLUDED_FILES:
            continue
        if any(part in EXCLUDED_DIRS for part in path.parts):
            continue
        if path.suffix.lower() not in EXCLUDED_SUFFIXES:
            files.append(path)
    return files


def scan_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    return [pattern.pattern for pattern in SECRET_PATTERNS if pattern.search(text)]


def main() -> int:
    findings = [(path, matches) for path in iter_files() if (matches := scan_file(path))]
    for path, matches in findings:
        relative = path.relative_to(ROOT)
        print(f"Potential secret in {relative}: {', '.join(matches)}")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
