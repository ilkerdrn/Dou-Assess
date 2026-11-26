# DOU Assess 6.57 — P0 Foundation Closure

- Canonical build metadata moved to `RELEASE.env`.
- API, deployment scripts and static asset version aligned to `6.57-p0-foundation-closure`.
- `/api/health` now always exposes non-secret release/build metadata, including in production.
- Added protected `/api/system/diagnostics` for DB/schema/storage/auth/OBS/security readiness.
- `Verify-Server.sh` and `Upgrade-Server.sh` source canonical release metadata instead of hard-coded version strings.
- Docker image includes `RELEASE.env`.
- Business schema remains `0031_medek_final_decision`; no academic/accreditation data migration is required.
