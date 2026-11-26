# DOU Assess 6.42 — Package Cleanup

Final distribution must contain no runtime SQLite database, no `.pytest_cache`, no `__pycache__`, and no `.pyc/.pyo`. Runtime data folders keep delivery placeholders only. `PACKAGE-MANIFEST-SHA256.txt` is regenerated after cleanup and verified after clean extraction.
