# Security Policy

## Supported Versions

Security fixes are accepted for the latest released version.

## Reporting a Vulnerability

Do not open a public issue for a suspected vulnerability.

Report security issues through GitHub private vulnerability reporting if it is
enabled for this repository. If that option is unavailable, contact the
maintainers through the repository owner.

Include:

- Affected version or commit.
- Steps to reproduce.
- Impact and affected data.
- Any relevant logs with secrets redacted.

## Secret Handling

The project is designed to receive secrets from environment variables. Never
commit:

- `.env` files.
- Slack bot tokens or signing secrets.
- Deploy keys.
- Git credentials.
- Generated board minutes containing private meeting content.

## Production Guidance

- Set `SLACK_SIGNING_SECRET` in production.
- Serve the app only behind HTTPS.
- Restrict git minutes publishing credentials to the target minutes repository.
- Rotate Slack and git credentials immediately if they are exposed.
