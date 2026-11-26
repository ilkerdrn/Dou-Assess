# DOU Assess 6.48 — MÜDEK Evaluator & Site Visit Control

## Scope
- MÜDEK previous-finding / interim-scope continuity
- Evaluator read-only snapshot enhanced with findings, visit notes and request SLA
- Accreditation finding registry: deficiency, weakness, concern, observation, strength
- Site-visit note registry with criterion linkage and visibility
- Document-request answer/close timestamps and SLA state
- Official 30-day response workflow after site visit
- UI Visit Control Center under Accreditation Lifecycle

## Key behavior
- For MÜDEK interim/monitoring applications, the previous general/renewal application is linked automatically.
- Open prior `weakness` findings are carried forward as monitoring items and form the primary interim scope.
- Site-visit → 30-day response transition sets an explicit 30-day institutional response deadline.
- Evaluator workspace remains read-only and snapshot-hashed.

## Schema
`0026_accreditation_visit_control`

## Validation
- pytest: 180/180 PASS
- Classic Scan Grading: PASS
- Legacy Classic Scan: PASS
- Complete Assessment Engine: PASS
- Lifecycle: PASS
- Pilot UAT 1–9: 41/41 PASS; accreditation_ready=true
- Fresh 0001→0026 migration: PASS
- Upgrade 0025→0026 migration: PASS
