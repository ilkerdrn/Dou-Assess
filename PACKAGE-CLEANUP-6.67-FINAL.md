# DOU Assess 6.67 — Final Package Cleanup

- Runtime SQLite/database files are excluded from the final release package.
- Test-generated evidence, scan and ops artifacts are removed; runtime directories retain `.gitkeep` placeholders only.
- `__pycache__`, `.pytest_cache`, `.pyc`, Playwright/test reports and temporary outputs are excluded.
- No `.env.internal`, live production secret file or secret directory is included.
- `.env.example`, `.env.pilot` and `.env.production.example` contain only placeholder/example values.
- `RELEASE.env` is the canonical non-secret release contract.
- `SOURCE-MANIFEST-SHA256.txt` is regenerated after cleanup and excludes itself.
- The final ZIP is reopened, integrity-tested and scanned for forbidden runtime artifacts before release sealing.
