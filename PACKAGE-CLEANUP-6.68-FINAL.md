# DOU Assess 6.68 — Final Package Cleanup

- Runtime SQLite/database files are excluded from the final release package.
- Test-generated evidence, scan and ops artifacts are removed; runtime directories retain `.gitkeep` placeholders only.
- `__pycache__`, `.pytest_cache`, `.pyc`, browser/test reports and temporary outputs are excluded.
- Generated automated backup artifacts are excluded.
- No `.env.internal`, live production password file or other runtime secret is included.
- `.env.example`, `.env.pilot` and `.env.production.example` contain only example/placeholder values.
- `RELEASE.env` is the canonical non-secret release contract.
- `SOURCE-MANIFEST-SHA256.txt` is regenerated after cleanup and excludes itself.
- The final ZIP is reopened, integrity-tested and scanned for forbidden runtime artifacts before release sealing.
