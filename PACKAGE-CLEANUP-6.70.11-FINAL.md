# Package Cleanup 6.70.11

- Test-generated evidence files removed.
- Test-generated scan files removed.
- Ops runtime files removed.
- `__pycache__` / `.pyc` / `.pytest_cache` removed.
- Local SQLite runtime database (`dou_assess.db`) removed.
- `.env.pilot` intentionally excluded from distributable ZIP.
- `.env.example` and `.env.production.example` remain as non-secret templates.
- No database dump, secret, runtime log or live configuration is packaged.
