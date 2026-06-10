# Operations Guide

## Required Runtime Configuration

Set these values for any production deployment:

- `BOARD_AUTH_TOKEN`: shared token for direct API routes.
- `BOARD_STATE_PATH`: JSON state file used to preserve active meetings,
  motions, votes, quorum records, and captured messages across process restarts.
- `SLACK_SIGNING_SECRET`: Slack request signing secret.
- `SLACK_BOT_TOKEN`: Slack bot token used for user lookup and history capture.

Optional git publishing values:

- `MINUTES_GIT_URL`
- `MINUTES_GIT_BRANCH`
- `MINUTES_GIT_PATH`
- `MINUTES_GIT_DIR`
- `MINUTES_GIT_AUTHOR_NAME`
- `MINUTES_GIT_AUTHOR_EMAIL`
- `MINUTES_GIT_SSH_KEY`

## Slack Configuration

Create two slash commands pointing to the same endpoint:

- `/board`: `https://<your-domain>/commands`
- `/vote`: `https://<your-domain>/commands`

Configure events:

- Events URL: `https://<your-domain>/events`
- Public channels: subscribe to message events and grant `channels:history`.
- Private channels: grant `groups:history` and invite the bot to the channel.

Recommended bot scopes:

- `commands`
- `chat:write`
- `users:read`
- `channels:history`
- `groups:history`

## Health Check

The unauthenticated health endpoint is:

```text
GET /health
```

Expected response:

```json
{"status":"ok"}
```

## Container Deployment

```bash
docker pull ghcr.io/quantyra/kuzuryu-board-meetings:latest
docker volume create board-meetings-data
docker run --env-file .env -p 8000:8000 \
  -v board-meetings-data:/data \
  ghcr.io/quantyra/kuzuryu-board-meetings:latest
```

Put the service behind HTTPS before connecting Slack.

Keep `BOARD_STATE_PATH` on a persistent volume in production. Open meetings are
stored there so slash commands can still find the active meeting after a
container restart or redeploy.

## Minutes Publishing

Use a deploy key with the narrowest possible access to the target minutes
repository. Mount the key into the container and set `MINUTES_GIT_SSH_KEY` to
the mounted path.

Generated minutes may contain private meeting records. Keep the minutes
repository access aligned with your organization record-retention policy.
