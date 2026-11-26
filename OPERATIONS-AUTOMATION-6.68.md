# DOU Assess 6.68 — Operations & Automation Runbook

## Runtime services
The canonical compose project contains four application-side roles:
- `api`: interactive HTTP/API traffic
- `worker`: durable background job processing
- `scheduler`: deadline/maintenance job generation
- `nginx`: HTTP edge inside the Docker project

PostgreSQL is the queue authority. Worker restarts do not delete queued jobs.

## Job types
- `evidence_integrity_scan`: verifies stored evidence against recorded SHA-256 values.
- `notification_sweep`: creates due/overdue notices idempotently.
- `backup_create`: creates and immediately verifies an operational backup.
- `backup_verify`: verifies the latest/specified backup artifact.
- `backup_prune`: removes backup directories older than configured retention.

## Scheduler
Scheduler execution is idempotent. Re-running a tick does not create a second notification for the same entity/deadline stage because notifications use stable dedupe keys.

Relevant configuration:
- `JOB_POLL_SECONDS`
- `JOB_STALE_MINUTES`
- `SCHEDULER_INTERVAL_SECONDS`
- `NOTIFICATION_LOOKAHEAD_DAYS`
- `EVIDENCE_INTEGRITY_INTERVAL_HOURS`
- `BACKUP_AUTOMATION_ENABLED`
- `BACKUP_INTERVAL_HOURS`
- `BACKUP_RETENTION_DAYS`

## Backups
Automated backup is off by default. Enabling it means creation/verification can run from the scheduler; it does not mean restore is automatic.

A valid backup contains a manifest and checksum information and must pass verification before the job is marked successful. Production DR acceptance still requires a controlled restore exercise to an isolated target and recorded RPO/RTO evidence.

## Notification center
Authenticated users receive only notifications matching their user email or role scope. Administrators can inspect all notifications. Users can mark individual notices or the whole inbox as read.

## Operational failure behavior
- stale `running` jobs can be re-queued after the stale threshold;
- failed jobs retry only while attempts remain;
- the API can continue serving interactive traffic if a worker job fails;
- backup jobs fail rather than returning a false success when dump/archive/checksum verification fails.

## Compose project identity
Production scripts resolve `COMPOSE_PROJECT_NAME` from the environment and pass it explicitly with `docker compose -p`. The Doğuş production fallback remains `dou-assess-619-final-server-ready`, preventing a versioned source-directory rename from silently creating new PostgreSQL/evidence/scan/ops volumes.
