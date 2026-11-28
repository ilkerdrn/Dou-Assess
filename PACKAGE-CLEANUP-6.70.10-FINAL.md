# Package Cleanup 6.70.10

Final package excludes:
- .env.pilot and other runtime env files
- local databases
- __pycache__ / .pytest_cache / *.pyc
- test-generated evidence/scans/ops payloads
- secrets

Only example env files are retained.
