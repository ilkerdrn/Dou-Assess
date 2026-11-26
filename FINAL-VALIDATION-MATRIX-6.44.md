# DOU Assess 6.44 — Final Validation Matrix

Validation date: **2026-09-14**  
Application version: `6.44-mudek-version-routing`  
Schema head: `0025_accreditation_compliance_core`

## Passed locally

- Python compile: PASS.
- JavaScript syntax: PASS.
- Bash syntax: PASS.
- Full pytest regression: **153/153 PASS**.
- Fresh Alembic chain through `0025_accreditation_compliance_core`: PASS.
- Upgrade Alembic chain `0024_mapping_contribution_1_5 -> 0025_accreditation_compliance_core`: PASS.
- MÜDEK 2.2 registry: 10 main criteria including historical Criterion 10: PASS.
- MÜDEK 3.0 registry: 9 main criteria + EK-1 under Criterion 5: PASS.
- MÜDEK 3.1 registry: 9 main criteria + EK-1 under Criterion 5: PASS.
- 2026-2027 general routing: 3.0 / 3.1 institution choice: PASS.
- 2026-2027 interim routing: 2.2: PASS.
- 2027-2028+ general routing: 3.1: PASS.
- Later interim routing: previous general-evaluation criteria version inheritance when known: PASS.
- Backend application framework guard: PASS.
- Quality360 dynamic MÜDEK routing UI: PASS.
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
- Freeze the exact official accreditation-period source templates and obtain institutional Quality Unit sign-off.

## Interpretation

MÜDEK routing prevents a known wrong criteria version from being frozen into a new application snapshot. It does not replace the institution's responsibility to confirm the official application-period rules, especially for later interim/monitoring cases linked to an earlier general evaluation.
