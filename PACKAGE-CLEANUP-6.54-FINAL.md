# DOU Assess 6.54 — Package Cleanup

Final distribution requirements:
- no runtime SQLite DB
- no `.pytest_cache`
- no `__pycache__`
- no `.pyc/.pyo`
- no production `.env`
- no real secrets
- `data/evidence`, `data/scans`, `data/ops` only delivery placeholders
- source manifest generated after cleanup
- ZIP verified from a clean extraction
