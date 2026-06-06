# Architecture

Kuzuryu Board Meetings is a small ASGI service built with FastAPI.

## Request Flow

Slack slash commands and events arrive at the public HTTP service:

- `POST /commands` handles `/board` and `/vote`.
- `POST /events` handles Slack event verification and message capture.
- Direct API routes under `/board/...` support local and integration testing.

Slack request signatures are verified when `SLACK_SIGNING_SECRET` is configured.

## Core Modules

- `app.py`: FastAPI routes and Slack command dispatch.
- `store.py`: in-process meeting, quorum, message, motion, and vote state.
- `models.py`: typed records used throughout the service.
- `minutes.py`: Markdown minutes rendering.
- `slack.py`: Slack form parsing, user lookup, signature verification, and
  history helpers.
- `publisher.py`: optional git publishing for generated minutes.
- `config.py`: environment-based settings.

## Data Model

A meeting contains:

- Chair.
- Attendance records.
- Captured conversation messages.
- Motions.
- Votes and recusals.

Minutes are generated from the current meeting record and can be returned to
Slack or committed into a separate git repository.

## Persistence

The initial release uses in-process state. This keeps deployment simple, but it
means active meetings are not durable across process restarts unless minutes
have already been published. Persistent storage is a roadmap item.
