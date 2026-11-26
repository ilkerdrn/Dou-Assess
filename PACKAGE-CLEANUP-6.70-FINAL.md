# DOU Assess 6.70 — Package Cleanup Final

Release packaging rules applied after final 253/253 regression:

- Removed `__pycache__`, `.pytest_cache`, `.pyc`, local SQLite databases and test-generated runtime files.
- `data/evidence`, `data/scans`, and `data/ops` retain directory placeholders only.
- No `.env.internal`, production secrets, PostgreSQL dump, runtime backup, or user evidence is shipped.
- `requirements.lock` and CycloneDX `SBOM-6.70.cdx.json` are included.
- `SOURCE-MANIFEST-SHA256.txt` is regenerated from the cleaned tree.
- Final ZIP is integrity-tested and accompanied by a SHA-256 sidecar.
