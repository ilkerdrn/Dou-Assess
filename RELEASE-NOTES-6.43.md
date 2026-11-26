# DOU Assess 6.43 — Quality Framework Precision

**Version:** `6.43-quality-framework-precision`  
**Schema:** `0025_accreditation_compliance_core` (no migration bump)

## Goal

6.42 finalization baseline is preserved. 6.43 makes Quality360 useful at official accreditation subcriterion level instead of only top-level criterion cards.

## MEDEK v1.1

- 9 official criteria / 46 subcriteria represented in the framework profile.
- 10 MEDEK program-outcome reference labels exposed under criterion 3.
- 5.1 / 5.2 / 5.3 curriculum thresholds continue to use the existing explainable AKTS checker.
- Each subcriterion carries expected evidence and an automation/manual verification mode.

## MÜDEK v3.1

- 9 official criteria / 32 normalized subcriteria represented in the framework profile.
- 11 MÜDEK outcome reference labels exposed under criterion 3.
- Removed the legacy phantom “criterion 10” signal.
- EK-1 is modeled correctly as discipline-specific education-plan content under criterion 5.1, not a separate tenth criterion.

## Exact evidence readiness

- Evidence can be linked directly to `3.1`, `3.2`, `5.4`, etc.
- Parent-criterion evidence is visible to the branch but does **not** silently satisfy a subcriterion.
- Readiness reports `ready / attention / gap` per subcriterion.
- Manual-review requirements stay explicit and can be recorded with 1–5 maturity without generating a fake automated pass.
- Priority gaps and Action Center recommendations now surface the concrete subcriterion and expected evidence.

## UI

- Quality360 top-level cards show subcriterion counts.
- Accreditation readiness expands each criterion into official subcriteria.
- Evidence and PUKÖ selectors expose both parent and subcriterion codes.
- Manual-review-only subcriteria can be verified inline by an authorised quality user.

## Validation

- Full pytest regression: **148/148 PASS**.
- Classic Scan Grading acceptance: **PASS**.
- Complete Assessment Engine acceptance: **PASS**.
- Legacy Classic Scan acceptance: **PASS**.
- Lifecycle acceptance: **PASS**.
- Pilot UAT 1–9: **41/41 PASS**, `accreditation_ready=true`.
