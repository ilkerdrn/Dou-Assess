# DOU Assess 6.46 — MEDEK Version Routing + Programa Özgü Çıktılar

**Version:** `6.46-medek-version-routing`  
**Schema:** `0025_accreditation_compliance_core` (no new migration)

6.45 MEDEK ÖDR Evidence Matrix baseline is preserved. This release makes MEDEK criteria-version selection period-aware and adds explicit, versioned program-specific outcome mapping.

## Added
- MEDEK v1.1 / v2.0 version routing for general, renewal, interim and monitoring lifecycles.
- Backend guard: general/renewal evaluations before the 2028 evaluation period use v1.1; 2028+ general/renewal evaluations use v2.0.
- Interim/monitoring evaluations inherit the framework version used in the program's previous MEDEK general evaluation. Missing historical context blocks the lifecycle instead of guessing.
- MEDEK v2.0 registry expanded to **8 general criteria / 45 subcriteria / 11 general program outcomes**.
- v2.0 curriculum thresholds retained as explicit machine-readable rules: 60 AKTS professional, 20 AKTS program-specific-output support, 15 AKTS applied/current-technology component and 5 AKTS external-stakeholder contribution.
- Versioned MEDEK program-specific outcome catalog.
- `İnternet ve Ağ Teknolojileri`: v1.1 profile has 4 program-specific outputs; v2.0 profile has 5.
- Program-specific outputs map explicitly to local Program Outcomes through `ProgramOutcomeComponent.framework_component_code` (`PÖÇ1`, `PÖÇ2`, ...).
- Quality360 program-specific-output workspace with coverage percent, mapped/unmapped status and one-click mapping to the selected local PÇ.
- Unrecognized program names stay `manual_required`; they are never auto-green.
- MEDEK route endpoint can infer the previous general evaluation version from the program's accreditation history.

## Interpretation controls
- General MEDEK outcomes and program-specific MEDEK outputs are tracked independently.
- A local PÇ count is not treated as official MEDEK coverage unless an explicit framework mapping exists.
- v2.0 has no separate general Criterion 9 in the registry; program-specific outputs are attached to the Program Outcomes domain rather than being invented as a ninth criterion.
- This internal routing engine does not replace institutional verification of the exact official source documents for the target accreditation period.

## Official source metadata
- MEDEK Önlisans Program Ölçütleri v1.1 — KL-004, rev. 01 (2025-08-28).
- MEDEK Önlisans Program Ölçütleri v2.0 — KL-007, first publication 2026-04-08.
- MEDEK v2.0 publication announcement: v2.0 applies from the 2028 evaluation period for first/general re-evaluations; interim evaluations retain the criteria version used in the previous general evaluation.
