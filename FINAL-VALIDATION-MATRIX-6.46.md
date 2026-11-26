# DOU Assess 6.46 — Final Validation Matrix

Validation date: **2026-09-14**  
Application version: `6.46-medek-version-routing`  
Schema head: `0025_accreditation_compliance_core`

## Passed locally

- Python compile / compileall: PASS.
- JavaScript syntax (`node --check`): PASS.
- Bash syntax: PASS.
- Full clean-DB pytest regression: **164/164 PASS**.
- Fresh Alembic chain through `0025_accreditation_compliance_core`: PASS.
- Upgrade Alembic chain `0024_mapping_contribution_1_5 -> 0025_accreditation_compliance_core`: PASS.
- MEDEK v1.1 registry: **9 criteria / 46 subcriteria**: PASS.
- MEDEK v2.0 registry: **8 criteria / 45 subcriteria / 11 general PÇ**: PASS.
- General/renewal routing before 2028 -> v1.1: PASS.
- General/renewal routing 2028+ -> v2.0: PASS.
- Interim/monitoring previous-general-version inheritance: PASS.
- Missing historical general version blocks interim/monitoring: PASS.
- Backend application guard rejects invalid MEDEK period/version combinations: PASS.
- `İnternet ve Ağ Teknolojileri` versioned program-specific profile: **v1.1 = 4 / v2.0 = 5 outputs**: PASS.
- Explicit local PÇ -> official program-specific-output mapping and coverage calculation: PASS.
- Unknown program catalog is `manual_required`, not automatic pass: PASS.
- Quality360 MEDEK route + program-specific mapping UI contract: PASS.
- Classic Scan Grading acceptance: PASS.
- Legacy Classic Scan acceptance: PASS.
- Complete Assessment Engine acceptance: PASS.
- Lifecycle acceptance: PASS.
- Pilot UAT 1–9: **41/41 PASS**, `accreditation_ready=true`.

## Institutional/site gates still required

- Real Microsoft Entra tenant/client/scope/role acceptance.
- Real Proliz/OBS contract and reconciliation acceptance.
- Production Docker/PostgreSQL/NGINX + TLS/DNS acceptance.
- Physical ADF/OMR field acceptance.
- Target-server load, backup/restore and DR rehearsal.
- Freeze the exact official MEDEK source templates for the target application period and obtain Quality Unit sign-off.
