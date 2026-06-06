# Changelog

All notable changes to Kuzuryu Board Meetings will be documented in this file.

The project follows semantic versioning for public releases.

## v0.1.1 - 2026-06-06

- Added best-practice open source governance files, issue templates, pull
  request template, support guidance, roadmap, and maintainer ownership.
- Added CodeQL, OpenSSF Scorecard, Dependabot, release notes configuration, and
  stricter workflow permissions.
- Added Docker OCI labels, `.dockerignore`, SBOM/provenance publishing, and
  Node 24 opt-in for Docker GitHub Actions.
- Added operations and architecture documentation.
- Increased test coverage to 81% and enforced an 80% coverage floor.
- Expanded publisher and Slack helper tests.

## v0.1.0 - 2026-06-06

- Initial AGPL-3.0-or-later release.
- Added Slack `/board` and `/vote` command handling.
- Added quorum, motion, vote, recusal, and minutes rendering support.
- Added optional git publishing for generated minutes.
- Added CI for linting, tests, radon complexity, radon maintainability index,
  security sweep, and Docker smoke validation.
- Published GHCR container tags `v0.1.0` and `latest`.
