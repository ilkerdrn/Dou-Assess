# DOU Assess 6.47 — Package Cleanup

Final distribution contains no runtime SQLite database, no `.pytest_cache`, no `__pycache__`, and no `.pyc/.pyo`. `data/evidence`, `data/scans`, and `data/ops` retain delivery placeholders only. `PACKAGE-MANIFEST-SHA256.txt` is regenerated only after final source/documentation cleanup and is independently verified after clean ZIP extraction.
