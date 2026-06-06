# Contributing

Thank you for considering a contribution to Kuzuryu Board Meetings.

## Before You Start

- Read `README.md` for setup and operating context.
- Read `SECURITY.md` before reporting vulnerabilities.
- Keep secrets out of commits. Do not paste Slack tokens, signing secrets,
  deploy keys, `.env` files, generated minutes repositories, or customer data.

## Local Development

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

Run the local checks before opening a pull request:

```bash
ruff check .
pytest
radon cc src tests -s -a
radon mi src tests -s
python scripts/security_sweep.py
```

## Pull Requests

Pull requests should:

- Explain the problem and the change.
- Include focused tests for behavior changes.
- Keep unrelated refactors out of the diff.
- Preserve AGPL-3.0-or-later licensing.
- Avoid adding new runtime dependencies unless they materially simplify the
  service or improve security.

## Commit and Review Standards

- Prefer small, reviewable commits.
- Use clear commit messages written in the imperative mood.
- Treat CI failures as blockers unless the failure is unrelated infrastructure.

## Developer Certificate of Origin

By contributing, you certify that you have the right to submit the work and that
it may be distributed under AGPL-3.0-or-later.
