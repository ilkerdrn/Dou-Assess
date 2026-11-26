# DOU Assess 6.62 — Final Package Cleanup

- Runtime SQLite/database files are excluded from the final release package.
- Test-generated evidence, scan and ops artifacts are removed; runtime directories retain `.gitkeep` placeholders only.
- `__pycache__`, `.pytest_cache`, `.pyc`, temporary test outputs and local secrets are excluded.
- `RELEASE.env` is the canonical non-secret build/version contract.
- Source manifest is regenerated after cleanup and excludes itself.
- Final ZIP is re-opened and checked for forbidden runtime artifacts before release sealing.
