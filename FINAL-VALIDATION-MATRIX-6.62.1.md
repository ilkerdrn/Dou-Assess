# DOU Assess 6.62.1 — Canonical PostgreSQL Hotfix Validation

- Application capability: `6.62-program-assessment-assurance`
- Release: `6.62.1`
- Expected schema head: `0036_program_assessment_assurance`

## Required release gates

- PostgreSQL boolean-literal regression test: PASS required.
- Full pytest regression: PASS required.
- Existing 6.62 Program Assessment Assurance acceptance tests: PASS required.
- Python source compilation: PASS required.
- Clean delivery tree: no runtime DB, `.pytest_cache`, `__pycache__`, `.pyc/.pyo`.
- `data/evidence`, `data/scans`, `data/ops`: delivery placeholders only.
- `SOURCE-MANIFEST-SHA256.txt`: regenerated after cleanup.
- ZIP integrity and external SHA-256: PASS required.

## Production upgrade note

The production server uses Compose project `dou-assess-619-final-server-ready`; PostgreSQL, evidence, scan and ops volumes must remain attached to that same project identity during upgrades. Never use `docker compose down -v` or volume-pruning commands as part of an application update.
