# DOU Assess 6.47 — MÜDEK EK-1 + Evidence Room Readiness

Release version: `6.47-mudek-ek1-evidence-room`

## Scope

This release deepens the MÜDEK accreditation workspace without changing the canonical assessment schema.

- MÜDEK 3.1 EK-1 discipline-specific curriculum topics are evaluated under Criterion 5.1, not as Program Outcomes and not as a fictional Criterion 10.
- EK-1 internal tracking codes are standardized across catalog, API, evidence, manual review and evidence-room export.
- Built-in exact profiles cover Computer/Software/AI, Electrical/Electronics/Communications/Control, and Industrial Engineering families.
- Unmatched program names remain `manual_review_required`; they are never auto-green.
- EK-1 readiness conservatively requires curriculum signal, exact evidence and framework-scoped manual maturity where applicable.
- BBO/FBO readiness follows the detailed MÜDEK Virtual Evidence Rooms structure.
- BBO tracks program evidence such as 1.2, 2.3, 3.2, separate MÇ-1…MÇ-11 evidence under 3.3, 4.1/4.2, 5.5 and 7.x.
- FBO tracks faculty/university evidence such as common courses, laboratories/experiments, remote learning, accessibility, safety, library, IT infrastructure and health services.
- BBO is program-scoped. FBO evidence is reusable only by programs that belong to the same faculty; evidence from another faculty cannot satisfy readiness.
- Exact room-item evidence, supporting criterion evidence, automatic system signals and manual maturity review are separated.
- BBO/FBO ZIP export uses detailed folder routing, embeds `KANIT-HAZIRLIK-MATRISI.json`, preserves framework version and records source program metadata.
- Mandatory EK-1/BBO/FBO gaps are surfaced in Action Center as actionable PUKÖ recommendations with owner, due date and expected evidence.
- Quality360 UI exposes EK-1 and evidence-room readiness, direct evidence navigation, manual review and BBO/FBO export.

## Validation

- Full pytest regression: **175/175 PASS**.
- Classic Scan Grading acceptance: PASS.
- Legacy Classic Scan acceptance: PASS.
- Complete Assessment Engine acceptance: PASS.
- Lifecycle acceptance: PASS.
- Pilot UAT 1–9: **41/41 PASS**, `accreditation_ready=true`.
- Python compile, JavaScript syntax and Bash syntax: PASS.
- Fresh Alembic migration to `0025_accreditation_compliance_core`: PASS.
- Upgrade migration `0024_mapping_contribution_1_5 -> 0025_accreditation_compliance_core`: PASS.
