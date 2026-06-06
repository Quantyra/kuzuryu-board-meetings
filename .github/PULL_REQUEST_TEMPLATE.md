## Summary

## Verification

- [ ] `ruff check .`
- [ ] `pytest`
- [ ] `radon cc src tests -s -a`
- [ ] `radon mi src tests -s`
- [ ] `python scripts/security_sweep.py`

## Security Checklist

- [ ] No secrets, tokens, deploy keys, `.env` files, or private meeting records.
- [ ] New Slack scopes or data retention changes are documented.
- [ ] Production behavior keeps Slack signature verification available.
