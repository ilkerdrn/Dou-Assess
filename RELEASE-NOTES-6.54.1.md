# DOU Assess 6.54.1 — Deploy Hotfix

Application code and database schema are unchanged from 6.54.

Deploy-only fixes:
- HTTP_PORT is read from `.env` by install/upgrade smoke checks.
- Backup directories are private (`umask 077`, mode 700).
- Restore verifies backup SHA-256 checksums when available.
- Preflight checks PostgreSQL secret file permissions.

Application: `6.54-final-production-release`
Schema: `0031_medek_final_decision`
