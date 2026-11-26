# DOU Assess 6.68 — Operations & Automation

## Release contract
- App version: `6.68-operations-automation`
- Schema: `0040_operations_automation`
- Parent schema: `0039_evidence_integrity_security`

## Scope
6.68 turns operationally heavy and deadline-driven work into durable, observable runtime flows without changing the accreditation domain model or adding Redis/Celery.

### Durable job execution
- PostgreSQL-backed `operational_jobs` queue.
- Separate `worker` container claims queued work and safely recovers stale jobs.
- Retry with bounded attempts and delayed retry.
- Integrity scans and operational backups no longer need to block the API request lifecycle.

### Scheduler and notifications
- Separate `scheduler` container runs idempotent operational ticks.
- Due-date notifications cover PUKÖ/QualityCycle, Quality Calendar, accreditation document requests, accreditation findings and Assessment Assurance items.
- Deadline stages include overdue, due today and configurable look-ahead reminders.
- User-facing notification center shows unread count, active notices, read state and contextual navigation.

### Verified backup automation
- Manual backup job is available to administrators.
- Scheduled backups are opt-in with `BACKUP_AUTOMATION_ENABLED` and remain disabled by default.
- A backup is successful only after SHA-256 manifest validation, tar validation and PostgreSQL dump listing verification when PostgreSQL is used.
- Retention pruning is supported.
- Restore is deliberately not automated against production; restore remains an explicit disaster-recovery rehearsal and acceptance gate.

### Operations center
- Paginated job history and notification inbox APIs.
- Central runtime summary for queued/running/failed jobs, backup state and automation configuration.
- Existing Evidence Integrity scan is available as an asynchronous worker job.

## Non-goals
- Entra and OBS integration behavior is unchanged.
- No new accreditation framework or criterion mapping is introduced.
- No automatic production restore is performed.
