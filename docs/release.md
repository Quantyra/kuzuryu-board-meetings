# Release Guide

This project releases source and containers from protected `main`.

## Release Requirements

Before publishing a release:

- `main` must be protected.
- Release changes must go through a pull request.
- Required checks must pass:
  - `quality`
  - `docker-smoke`
  - `CodeQL`
  - `OpenSSF Scorecard`
- At least one code-owner review must approve the pull request.
- The working tree must be clean.
- The release tag must point at the intended `main` commit.

## Version Bump

Update:

- `pyproject.toml`
- `CHANGELOG.md`

Use semantic versioning for public releases.

## Local Verification

Run:

```bash
ruff check .
pytest
radon cc src tests -s -a
radon mi src tests -s
python scripts/security_sweep.py
```

## Protected-Branch Flow

Create a release branch:

```bash
git switch -c release/vX.Y.Z
git push -u origin release/vX.Y.Z
```

Open a pull request into `main`. After checks and code-owner review pass, merge
the pull request. Do not bypass branch protection for normal releases.

## GitHub Release

Create the GitHub release from the merged `main` commit:

```bash
gh release create vX.Y.Z \
  --repo Quantyra/kuzuryu-board-meetings \
  --target <main-sha> \
  --title "vX.Y.Z" \
  --notes-file <release-notes-file>
```

The `Publish Container` workflow runs on published releases.

## Container Publishing

Published release tags push:

- `ghcr.io/quantyra/kuzuryu-board-meetings:vX.Y.Z`
- `ghcr.io/quantyra/kuzuryu-board-meetings:latest`

The workflow also requests SBOM and provenance attestations.

## Public Pull Verification

After a container publish, verify anonymous pull access:

```bash
docker pull ghcr.io/quantyra/kuzuryu-board-meetings:vX.Y.Z
docker pull ghcr.io/quantyra/kuzuryu-board-meetings:latest
```

If anonymous pull fails with `401 Unauthorized`, make the GHCR package public:

1. Open the Quantyra organization on GitHub.
2. Go to Packages.
3. Open `kuzuryu-board-meetings`.
4. Open package settings.
5. Change visibility to public.

Do not claim the container is publicly installable until anonymous pull is
verified.
