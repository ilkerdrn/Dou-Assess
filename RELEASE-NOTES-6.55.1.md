# DOU Assess 6.55.1 — Premium Production Final

This package combines the validated 6.55 Premium Academic UX with the complete 6.54.1 production deploy hardening layer.

## Included
- Premium Academic UX / institutional higher-education visual system
- Open academic navigation shell and improved typography
- Role/action-centered dashboard hierarchy
- Quality360 / MEDEK / MÜDEK readability improvements
- Student Outcome Card readability improvements
- Production Docker Compose
- Preflight / install / upgrade / verify / backup / restore / go-live scripts
- Persistent compose project naming (`dou_assess`)
- HTTP_PORT-aware smoke checks
- Backup directory permission hardening and restore checksum validation

## Application and schema
Application logic remains the validated production baseline.
Schema head remains `0031_medek_final_decision`.
No database migration is introduced by this UX/deploy consolidation release.
