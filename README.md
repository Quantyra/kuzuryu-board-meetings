# Kuzuryu Board Meetings

[![CI](https://github.com/Quantyra/kuzuryu-board-meetings/actions/workflows/ci.yml/badge.svg)](https://github.com/Quantyra/kuzuryu-board-meetings/actions/workflows/ci.yml)
[![Security](https://github.com/Quantyra/kuzuryu-board-meetings/actions/workflows/security.yml/badge.svg)](https://github.com/Quantyra/kuzuryu-board-meetings/actions/workflows/security.yml)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPLv3-blue.svg)](LICENSE)

Kuzuryu Board Meetings is an AGPL Slack application for board meeting quorum,
motions, votes, recusals, conversation capture, and markdown minutes publishing.

It provides two Slack slash commands:

- `/board`: start, update quorum, list quorum, and close a meeting.
- `/vote`: create motions, cast votes, record recusals, and close motions.

Minutes can be returned directly to Slack and optionally committed into a git
repository for durable records.

## Quick Start

```bash
cp .env.example .env
docker pull ghcr.io/quantyra/kuzuryu-board-meetings:latest
docker volume create board-meetings-data
docker run --env-file .env -p 8000:8000 \
  -v board-meetings-data:/data \
  ghcr.io/quantyra/kuzuryu-board-meetings:latest
```

Then open:

```text
http://127.0.0.1:8000/docs
```

For production setup, see `docs/operations.md`.

## Security Model

Secrets are supplied through environment variables. Do not commit `.env` files,
Slack tokens, signing secrets, deploy keys, or generated minutes repositories.

Recommended Slack bot scopes:

- `commands`
- `chat:write`
- `users:read`
- `channels:history`
- `groups:history`

Use `SLACK_SIGNING_SECRET` in production so Slack request signatures are
verified.

Report vulnerabilities through the process in `SECURITY.md`.

## Local Setup

1. Create a virtual environment:

   ```bash
   python -m venv .venv
   . .venv/bin/activate
   ```

2. Install the project:

   ```bash
   pip install -e ".[dev]"
   ```

3. Configure local environment:

   ```bash
   cp .env.example .env
   ```

   Set `BOARD_AUTH_TOKEN` to any local shared secret. Leave Slack secrets blank
   for local API-only testing.

4. Run the API:

   ```bash
   uvicorn kuzuryu_board_meetings.app:create_app --factory --reload
   ```

5. Open the API docs:

   ```text
   http://127.0.0.1:8000/docs
   ```

## Slack Setup

Create a Slack app at `https://api.slack.com/apps`.

Slash command URLs:

- `/board`: `https://<your-domain>/commands`
- `/vote`: `https://<your-domain>/commands`

Events URL:

- `https://<your-domain>/events`

Subscribe to message events for the channel types you use. Public channel
history needs `channels:history`; private channels need `groups:history` and the
bot must be invited to the channel.

## Cloud Setup

The service is a normal ASGI app and can run behind any HTTPS reverse proxy.

### Docker

Pull the published container:

```bash
docker pull ghcr.io/quantyra/kuzuryu-board-meetings:latest
docker run --env-file .env -p 8000:8000 ghcr.io/quantyra/kuzuryu-board-meetings:latest
```

Or build locally:

```bash
docker build -t kuzuryu-board-meetings .
docker run --env-file .env -p 8000:8000 kuzuryu-board-meetings
```

### Docker Compose

```bash
docker compose -f deploy/docker-compose.yml up -d
```

### Managed Cloud

For Render, Fly.io, Railway, ECS, Cloud Run, or Kubernetes:

1. Build the Docker image.
2. Expose port `8000`.
3. Set the environment variables from `.env.example`.
4. Put the app behind HTTPS.
5. Point Slack slash commands and events to the public HTTPS routes.

## Git Minutes Publishing

Set these environment variables to publish minutes into a git repository:

- `MINUTES_GIT_URL`
- `MINUTES_GIT_BRANCH`
- `MINUTES_GIT_PATH`
- `MINUTES_GIT_DIR`
- `MINUTES_GIT_AUTHOR_NAME`
- `MINUTES_GIT_AUTHOR_EMAIL`

## Runtime State

Set `BOARD_STATE_PATH` to a JSON file on persistent storage. The published
container defaults to `/data/board-state.json`; mount `/data` as a Docker volume
so active meetings, quorum records, motions, votes, and captured messages
survive container restarts.
- `MINUTES_GIT_SSH_KEY`

For private repositories, mount a read/write deploy key and set
`MINUTES_GIT_SSH_KEY` to the in-container key path.

## Development Gates

Run all local gates:

```bash
ruff check .
pytest
radon cc src tests -s -a
radon mi src tests -s
python scripts/security_sweep.py
```

The GitHub Actions workflow runs these same checks on pull requests and pushes.

## Project Resources

- `docs/operations.md`: production setup, Slack configuration, and runtime
  guidance.
- `docs/architecture.md`: service architecture and module map.
- `docs/release.md`: release, container publishing, and public pull
  verification process.
- `CONTRIBUTING.md`: contribution workflow.
- `SECURITY.md`: vulnerability reporting and production security guidance.
- `ROADMAP.md`: planned improvements and non-goals.
- `CHANGELOG.md`: release history.
