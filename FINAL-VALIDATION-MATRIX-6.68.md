# DOU Assess 6.68 — Final Validation Matrix

- Version: `6.68-operations-automation`
- Schema: `0040_operations_automation`
- Targeted 6.68 + 6.67 security regression: **12/12 PASS**.
- Full regression: **241/241 PASS**.
- Fresh migration `0001 -> 0040`: **PASS**.
- Realistic upgrade `0039 -> 0040`: **PASS**.
- New `operational_jobs` and `operational_notifications` tables exist on both migration paths.
- JavaScript syntax: **PASS**.
- Python compile: **PASS**.
- Server shell syntax (`Install/Upgrade/Backup/Restore/Preflight/Verify`): **PASS**.
- Standard and production Compose YAML structure: **PASS** (`db`, `migrate`, `api`, `worker`, `scheduler`, `nginx`).
- Docker Compose CLI runtime validation was not available in the packaging environment; `Preflight-Server.sh` performs `docker compose ... config` on the target server before deployment.
- Deployment tooling preserves the explicit Compose project identity and therefore the existing named volumes.
- Backup tooling validates SHA-256, tar readability and PostgreSQL dump listing before reporting the deploy backup path.
- Restore tooling stops API, worker and scheduler before destructive database restore and restarts them only after migration.

## 6.68 capability closure
- PostgreSQL-backed durable job queue: PASS.
- Concurrent-safe PostgreSQL claim path (`FOR UPDATE SKIP LOCKED`): covered by implementation; SQLite fallback used in local tests.
- Stale worker recovery + bounded retry: PASS through service regression.
- Separate worker/scheduler runtime definitions: PASS.
- Idempotent deadline notification generation: PASS.
- User-facing notification center/read state/context navigation: PASS through static/runtime contract tests.
- Async evidence-integrity job: PASS.
- Operational backup creation + verification: PASS.
- Operations job/notification pagination: PASS.
- Clean source manifest: **370 files** before `SOURCE-MANIFEST-SHA256.txt`; runtime data directories contain `.gitkeep` only.

## Production acceptance boundaries
A successful source/migration test does not auto-pass the institution's off-site restore/DR rehearsal, physical OMR benchmark, official accreditation-template sign-off or real-program UAT. Automated backup is intentionally disabled by default until the institution chooses the off-site destination/retention policy. Entra and OBS are outside the 6.68 scope.
