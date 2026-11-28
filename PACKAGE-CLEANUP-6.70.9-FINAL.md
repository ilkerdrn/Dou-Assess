# Package Cleanup — 6.70.9 Final

Removed before packaging:
- Python/test caches
- local DB/sqlite files
- runtime env/secrets
- generated evidence/scans/ops payloads

Kept runtime data directories only with `.gitkeep` placeholders.
