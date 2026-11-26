# DOU Assess 6.64 — Integration Acceptance Guard

- Current schema head remains `0037_institutional_accreditation_readiness`; this release is configuration/runtime hardening and adds no new database tables.
- OBS is read-only by default (`OBS_WRITEBACK_ENABLED=false`).
- `/api/courses/{course_id}/obs-results/push` returns 403 unless institutional write-back approval is explicitly enabled.
- When enabled, the existing endpoint/HTTPS/token/audit controls remain in force.
- Public auth config exposes only OBS readiness booleans/mode and never secret values.
- Pilot readiness treats read-only mode as the safe default and surfaces write-back configuration separately.
- The OBS UI no longer presents the platform as two-way by default and hides the write-back action until enabled.
